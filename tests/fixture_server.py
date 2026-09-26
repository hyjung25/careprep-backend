"""LOCAL SOFTWARE TEST ONLY. Never deploy this module. No live AI calls.
Run: .venv/bin/uvicorn tests.fixture_server:app --port 8001 --no-access-log
"""
import asyncio
import json
from fastapi import HTTPException
from app import main, provider
from app.schemas import ChatSelection, SummarySelection

async def fixture(prompt, payload, model_class):
    await asyncio.sleep(0.3)
    if model_class is ChatSelection:
        message = payload['message']
        if message == 'TEST_ERROR': raise HTTPException(502, detail={'code':'provider_failed'})
        if message == 'TEST_RATE': raise HTTPException(429, detail={'code':'rate_limited'})
        if message == 'TEST_TIMEOUT': raise HTTPException(504, detail={'code':'provider_timeout'})
        if message == 'TEST_DELAY': await asyncio.sleep(3)
        return ChatSelection(urgent=False,boundary=False,
            passage_ids=[r['id'] for r in payload['resources']],
            question_ids=['severity'] if not payload['history'] else ['associated'])
    users = payload['user_messages']
    return SummarySelection(main_concern=[0],onset_duration=[0],
        severity_progression=[1] if len(users)>1 else [], associated_symptoms=[],
        medications_allergies=[],clinician_questions=[])

provider.generate = fixture

# Label EVERY success response; the production application has no mock switch.
async def app(scope, receive, send):
    if scope['type'] != 'http':
        return await main.app(scope, receive, send)
    chunks, start = [], None
    async def labeled(event):
        nonlocal start
        if event['type'] == 'http.response.start':
            start = event
        elif event['type'] == 'http.response.body':
            chunks.append(event.get('body', b''))
            if not event.get('more_body', False):
                raw = b''.join(chunks)
                if start['status'] == 200 and scope['method'] != 'OPTIONS':
                    data = json.loads(raw)
                    data['development_fixture'] = True
                    raw = json.dumps(data).encode()
                start['headers'] = [(k,v) for k,v in start['headers'] if k != b'content-length']
                start['headers'].append((b'content-length', str(len(raw)).encode()))
                await send(start)
                await send({'type':'http.response.body','body':raw})
    await main.app(scope, receive, labeled)
