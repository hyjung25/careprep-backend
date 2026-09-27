import os
import asyncio
import time
from collections import deque
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from . import provider
from .schemas import (ChatRequest, ChatResponse, ChatSelection, SummaryRequest,
                      SummaryResponse, SummarySelection, SummarySection, SummaryAudit)
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
    previous_replies = [m.content for m in data.history if m.role == 'assistant']
    # Compare actual rendered passages, not user-supplied citation markers alone.
    fresh = [r for r in chosen if not any(
        r['en'] in reply or r['ko'] in reply for reply in previous_replies)]
    asked = {qid for qid, translations in QUESTIONS.items()
             if any(q in reply for q in translations for reply in previous_replies)}
    questions = [q for q in dict.fromkeys(selection.question_ids) if q not in asked]
    questions = questions[:1 if previous_replies else 2]
    parts = []
    if previous_replies:
        if len(data.message) <= 400:
            parts.append(localized(('Added to your visit notes, in your words:',
                                    '진료 메모에 다음 내용을 본인의 표현 그대로 반영할게요:'), data.language)
                         + '\n“' + data.message + '”')
        else:
            parts.append(localized(('Thanks for the additional detail. I’ll use it when organizing your visit notes.',
                                    '자세히 알려주셔서 감사합니다. 진료 메모를 정리할 때 반영할게요.'), data.language))
    if fresh:
        parts.append(localized(('General information', '일반적인 정보'), data.language))
        parts.extend(r[data.language] + ' [' + r['id'] + ']' for r in fresh)
    elif chosen:
        parts.append(localized(('Reference for this topic:', '이 주제의 참고 자료:'), data.language)
                     + ' ' + ' '.join('[' + r['id'] + ']' for r in chosen))
    if not chosen and not previous_replies:
        parts.append(localized(INSUFFICIENT, data.language))
    elif not chosen:
        parts.append(localized(('I don’t have additional source-backed guidance for that detail.',
                                '추가로 알려주신 내용에 대해 출처로 뒷받침할 수 있는 안내가 충분하지 않습니다.'), data.language))
    if questions:
        parts.extend(localized(QUESTIONS[q], data.language) for q in questions)
    else:
        parts.append(localized(('You can add anything else you want the clinician to know, or generate your visit summary.',
                                '의료진에게 알리고 싶은 내용을 더 말씀하시거나 진료 요약을 만들어 보세요.'), data.language))
    return ChatResponse(response='\n\n'.join(parts), sources=[source(r) for r in chosen], mode='ai')

@api.post('/api/summary', response_model=SummaryResponse)
async def summary(data: SummaryRequest, request: Request):
    rate_check(request)
    users = [m.content for m in data.history if m.role == 'user']
    try:
        # One total deadline for drafting + independent grounding review.
        async with asyncio.timeout(38):
            selection = await provider.generate(provider.SUMMARY_PROMPT,
                {'language': data.language, 'user_messages': users}, SummarySelection)
            for facts in selection.model_dump().values():
                for fact in facts:
                    for evidence in fact['evidence']:
                        i, quote = evidence['message_id'], evidence['quote']
                        if type(i) is not int or not 0 <= i < len(users) or quote not in users[i]:
                            raise HTTPException(502, detail={'code': 'invalid_provider_output'})
            audit = await provider.generate(provider.SUMMARY_AUDIT_PROMPT,
                {'user_messages': users, 'draft': selection.model_dump()}, SummaryAudit)
            if not audit.valid:
                raise HTTPException(502, detail={'code': 'invalid_provider_output'})
    except TimeoutError:
        raise HTTPException(504, detail={'code': 'provider_timeout'}) from None
    sections, unknowns, text = [], [], [localized(('Visit summary · user-reported', '진료 요약 · 사용자 진술'), data.language)]
    for key, facts in selection.model_dump().items():
        title = localized(FIELDS[key], data.language)
        notes = list(dict.fromkeys(f['text'] for f in facts))
        evidence = [e for f in facts for e in f['evidence']]
        sections.append(SummarySection(key=key, title=title, notes=notes,
            quotes=[e['quote'] for e in evidence], message_ids=[e['message_id'] for e in evidence]))
        if notes:
            text.append(title + '\n' + '\n'.join('- ' + note for note in notes))
        elif key not in ('relevant_context', 'clinician_questions'):
            unknowns.append(title)
    if not selection.clinician_questions:
        text.append(localized(('Questions for the clinician\nNo visit questions specified yet.',
                                '의료진에게 할 질문\n아직 진료 때 할 질문을 지정하지 않았습니다.'), data.language))
    if unknowns:
        text.append(localized(('Still to clarify: ', '추가 확인: '), data.language) + '; '.join(unknowns))
    text.append(localized(('Review before sharing. Based on the last 12 messages; not a diagnosis.',
                            '공유 전 확인하세요. 최근 메시지 12개를 바탕으로 하며 진단이 아닙니다.'), data.language))
    notice = localized(URGENT_TEXT, data.language) if URGENT.search('\n'.join(users)) else None
    if notice:
        text.insert(0, notice)
    return SummaryResponse(summary='\n\n'.join(text), sections=sections,
                           important_unknowns=unknowns, urgent_notice=notice)

# CORS wraps errors and the body limiter too; use precise origins, not a wildcard.
app = CORSMiddleware(RequestLimits(api), allow_origins=[s.strip() for s in
    os.getenv('ALLOWED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500').split(',') if s.strip()],
    allow_methods=['GET', 'POST'], allow_headers=['Content-Type'], expose_headers=['Retry-After'])
