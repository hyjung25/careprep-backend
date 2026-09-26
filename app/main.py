import os
import time
from collections import deque
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from . import provider
from .schemas import (ChatRequest, ChatResponse, ChatSelection, SummaryRequest,
                      SummaryResponse, SummarySelection, SummarySection)
from .content import (QUESTIONS, FIELDS, URGENT, BOUNDARY, BOUNDARY_TEXT, URGENT_TEXT,
                      INSUFFICIENT, localized, retrieve, source)

load_dotenv()
api = FastAPI(title='CarePrep', version='1.0.0')

class RequestLimits:
    """Bound body BEFORE parsing (including chunked requests). No request logging."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            event = await receive()
            if event['type'] == 'http.disconnect':
                return
            size += len(event.get('body', b''))
            if size > 65536:
                return await JSONResponse({'detail': {'code': 'request_too_large'}}, 413)(scope, receive, send)
            chunks.append(event.get('body', b''))
            if not event.get('more_body', False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)

class Limiter:
    def __init__(self):
        self.clients = {}
        self.day = int(time.time() // 86400)
        self.count = 0

    def check(self, client):
        now = time.monotonic()
        self.clients = {k: v for k, v in self.clients.items() if v and v[-1] > now - 60}
        if len(self.clients) >= 2000 and client not in self.clients:
            raise HTTPException(429, detail={'code': 'rate_limited'}, headers={'Retry-After': '60'})
        hits = self.clients.setdefault(client, deque())
        while hits and hits[0] <= now - 60:
            hits.popleft()
        if len(hits) >= int(os.getenv('RATE_LIMIT_PER_MINUTE', '10')):
            raise HTTPException(429, detail={'code': 'rate_limited'}, headers={'Retry-After': '60'})
        hits.append(now)
        day = int(time.time() // 86400)
        if day != self.day:
            self.day, self.count = day, 0
        if self.count >= int(os.getenv('GLOBAL_DAILY_LIMIT', '200')):
            raise HTTPException(429, detail={'code': 'daily_limit'}, headers={'Retry-After': '3600'})
        self.count += 1

limiter = Limiter()

@api.middleware('http')
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@api.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    return JSONResponse({'detail': {'code': 'invalid_input'}}, 422)

@api.exception_handler(Exception)
async def unexpected(request, exc):
    return JSONResponse({'detail': {'code': 'internal_error'}}, 500)

@api.get('/health')
async def health():
    key = os.getenv('OPENAI_API_KEY', '').strip()
    return {'status': 'ok', 'provider_configured': bool(key and not key.startswith('replace-')),
            'prototype': True}

def urgent_response(language, resources):
    return ChatResponse(response=localized(URGENT_TEXT, language), urgent=True,
                        sources=[source(r) for r in resources], mode='safety')

def rate_check(request):
    # Deliberately do not trust caller-controlled X-Forwarded-For.
    limiter.check(request.client.host if request.client else 'unknown')

@api.post('/api/chat', response_model=ChatResponse)
async def chat(data: ChatRequest, request: Request):
    users = '\n'.join(m.content for m in data.history if m.role == 'user')
    resources = retrieve(data.message, users)
    # Safety response remains available even without credentials or quota.
    if URGENT.search(data.message + '\n' + users):
        return urgent_response(data.language, resources)
    rate_check(request)
    if BOUNDARY.search(data.message):
        return ChatResponse(response=localized(BOUNDARY_TEXT, data.language), sources=[], mode='boundary')
    selection = await provider.generate(provider.CHAT_PROMPT, {
        'language': data.language, 'message': data.message,
        'history': [m.model_dump() for m in data.history],
        'resources': resources, 'question_catalog': QUESTIONS,
    }, ChatSelection)
    if selection.urgent:
        return urgent_response(data.language, resources)
    if selection.boundary:
        return ChatResponse(response=localized(BOUNDARY_TEXT, data.language), sources=[], mode='boundary')
    allowed = {r['id']: r for r in resources}
    if any(s not in allowed for s in selection.passage_ids):
        raise HTTPException(502, detail={'code': 'invalid_provider_output'})
    chosen = [allowed[k] for k in dict.fromkeys(selection.passage_ids)]
    parts = [localized(('General information', '일반적인 정보'), data.language)]
    parts += [r[data.language] + ' [' + r['id'] + ']' for r in chosen]
    if not chosen:
        parts.append(localized(INSUFFICIENT, data.language))
    if selection.question_ids:
        parts.append(localized(('To understand what you want to discuss:', '진료 때 이야기할 내용을 더 알아볼게요:'), data.language))
        parts.extend(localized(QUESTIONS[q], data.language) for q in dict.fromkeys(selection.question_ids))
    else:
        parts.append(localized(('You can generate your visit summary whenever you are ready.', '준비되면 진료 요약을 만들어 보세요.'), data.language))
    return ChatResponse(response='\n\n'.join(parts), sources=[source(r) for r in chosen], mode='ai')

@api.post('/api/summary', response_model=SummaryResponse)
async def summary(data: SummaryRequest, request: Request):
    rate_check(request)
    users = [m.content for m in data.history if m.role == 'user']
    selection = await provider.generate(provider.SUMMARY_PROMPT,
        {'language': data.language, 'user_messages': users}, SummarySelection)
    sections, unknowns = [], []
    text = [localized(('Visit notes · user-reported, not a diagnosis', '진료 메모 · 사용자 진술이며 진단이 아닙니다'), data.language),
            localized(('Whole messages are quoted to preserve context. Check the grouping and bring corrections to your clinician. Only the last 12 conversation messages are included.',
                       '문맥 보존을 위해 메시지 전체를 인용합니다. 분류를 확인하고 의료진에게 수정 내용을 알려주세요. 최근 대화 12개만 포함됩니다.'), data.language)]
    for key, ids in selection.model_dump().items():
        if any(type(i) is not int or not 0 <= i < len(users) for i in ids):
            raise HTTPException(502, detail={'code': 'invalid_provider_output'})
        ids = list(dict.fromkeys(ids))
        title = localized(FIELDS[key], data.language)
        quotes = [users[i] for i in ids]
        sections.append(SummarySection(key=key, title=title, quotes=quotes, message_ids=ids))
        if not quotes:
            unknowns.append(title)
        text.append(title + '\n' + ('\n'.join('“' + q + '”' for q in quotes) if quotes else
                    localized(('Not provided', '제공되지 않음'), data.language)))
    text.append(localized(('Important unknowns', '확인이 필요한 정보'), data.language) + '\n' +
                (', '.join(unknowns) or localized(('No empty categories; completeness is not established.', '빈 항목은 없지만 정보의 완전성이 확인된 것은 아닙니다.'), data.language)))
    notice = localized(URGENT_TEXT, data.language) if URGENT.search('\n'.join(users)) else None
    if notice:
        text.insert(0, notice)
    return SummaryResponse(summary='\n\n'.join(text), sections=sections,
                           important_unknowns=unknowns, urgent_notice=notice)

# CORS wraps errors and the body limiter too; use precise origins, not a wildcard.
app = CORSMiddleware(RequestLimits(api), allow_origins=[s.strip() for s in
    os.getenv('ALLOWED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500').split(',') if s.strip()],
    allow_methods=['GET', 'POST'], allow_headers=['Content-Type'], expose_headers=['Retry-After'])
