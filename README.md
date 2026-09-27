# CarePrep backend

A small FastAPI service for an English/Korean educational health-visit preparation project. It retrieves curated MedlinePlus passages, asks relevant follow-up questions, and creates concise, evidence-backed visit notes from user messages. **It does not diagnose, prescribe, rule out serious illness, or provide validated triage.** Text only; no image uploads.

The separate [frontend repository](https://github.com/hyjung25/careprep-frontend) contains plain HTML/CSS/JavaScript for GitHub Pages. This repository deploys separately to Render. No database is used.

## Local setup

Requires Python 3.12 (the system Python on some Macs is too old).

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env locally: replace OPENAI_API_KEY with your own project API key.
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

Visit `http://127.0.0.1:8000/docs` for exact OpenAPI request/response schemas, or `/openapi.json` for machine-readable schemas. The server runs without a key, but normal AI chat and summaries return `503 provider_not_configured`. Fixed urgent/boundary responses do not need the provider. There is no production mock mode. Health reports configuration presence, not a successful provider authentication test.

## Configuration

| Variable | Default / purpose |
|---|---|
| `OPENAI_API_KEY` | Required for normal chat and summary; server only |
| `OPENAI_MODEL` | `gpt-4.1-mini`, a model supporting Responses structured outputs |
| `ALLOWED_ORIGINS` | Comma-separated exact frontend origins; local default `http://localhost:5500,http://127.0.0.1:5500` |
| `PROVIDER_TIMEOUT_SECONDS` | 25 seconds, capped at 40 |
| `RATE_LIMIT_PER_MINUTE` | 10 POST attempts per observed client address |
| `GLOBAL_DAILY_LIMIT` | 200 POST attempts per process per UTC day |

Use the **origin** `https://hyjung25.github.io`, not a repository path, in CORS. No wildcard, credentials, or authentication cookies are needed. CORS limits browsers; it is not authentication and cannot stop scripts from calling a public endpoint.

Never commit `.env` or keys. On Render use secret environment variables, not a file in Git. The `.env.example` contains placeholders only. Do not paste your key into the frontend, chat, screenshots, or demo video.

## Frontend calls and schemas

All POST requests and responses are JSON. Unknown fields are rejected. `language` is `en` (default) or `ko`. Each `content`/`message` is 1–1200 trimmed characters. History has at most 12 messages; each role is `user` or `assistant`. Body limit is 64 KiB even for chunked requests. The browser retains/sends only the most recent 12 messages.

### `GET /health`

Called by **Apply & check** in frontend connection settings; also Render's health check. Returns HTTP 200 even if provider credentials are missing:

```json
{"status":"ok","provider_configured":false,"prototype":true}
```

### `POST /api/chat`

Called on **Send message**, with prior history excluding the new message:

```json
{"message":"I have had a headache since yesterday.","history":[],"language":"en"}
```

Response shape (example selection; provider selections vary):

```json
{
  "response":"General information\n\nHeadaches have different causes. Sudden, severe headaches warrant contacting a healthcare professional. Seek medical help right away for a headache after a head injury, or a headache with a stiff neck, fever, confusion, loss of consciousness, or eye or ear pain. [headache]\n\nTo understand what you want to discuss:\n\nHow strong does it feel in your own words, and how does it affect your day?",
  "sources":[{"id":"headache","title":"Headache — MedlinePlus","url":"https://medlineplus.gov/headache.html","retrieved_at":"2026-09-26","attribution":"Source: MedlinePlus, National Library of Medicine."}],
  "urgent":false,
  "mode":"ai"
}
```

`mode` is `ai` (model-selected passages/questions), `safety` (fixed urgent response), or `boundary` (fixed refusal of diagnosis/medication requests). `urgent:false` is not a finding that a person is safe. Urgent phrase matches bypass the model/quota to avoid delaying help. The model can also flag urgency for messages not caught by those examples. Emergency text says “local emergency service”; no country or phone number is inferred from language.

### `POST /api/summary`

Called on **Generate visit summary**. Copying is local and does not call the backend.

```json
{"history":[{"role":"user","content":"I have a cough since Monday."}],"language":"en"}
```

Returns readable `summary` text, seven structured `sections`, `important_unknowns`, and an optional `urgent_notice`. Example section:

```json
{
  "key": "main_concern",
  "title": "Main concern",
  "notes": ["Cough"],
  "quotes": ["I have a cough since Monday."],
  "message_ids": [0]
}
```

Sections cover concern/location, onset/duration, severity/progression, associated symptoms, volunteered medications/allergies, **relevant context** (e.g. reported alcohol use without inferring causation), and explicitly requested clinician questions. Each section's `quotes` and `message_ids` are parallel evidence arrays; IDs index the user-only message list. `notes` are concise paraphrases, not whole-message duplicates. Empty clinical categories appear once in `important_unknowns`; no invented normal findings. Unknowns reflect empty categories, not an exhaustive clinical checklist (e.g. a medication entry does not establish allergy status).

Drafting uses a strict schema with at most two notes per category, 240 characters per note, and 1–3 supporting verbatim quotes per note. The backend rejects invalid IDs or quotes that do not occur in the cited messages. A **second independent model call** checks the draft against full user messages for unsupported facts, negation loss, causal claims, inappropriate clinician questions, or omitted material context. Failed review returns `502 invalid_provider_output`, never the unchecked draft. Valid excerpts alone do not establish semantic accuracy; the model reviewer can also err, so the interface asks users to review the notes and exposes supporting messages.

A generic “What should I do?” to the chatbot is not saved as a clinician question. No visit questions specified means exactly that; questions are not invented. Dates stay relative when the user provides them that way. No diagnoses, drug advice, or care plans are generated by the summary prompt.

Summary generation makes two provider calls, using at most 2200 output tokens for drafting and 700 for review, with a shared 38-second deadline; it therefore costs more than one chat turn. There are no automatic retries. Source clinical guidance in chat remains server-rendered; the summary's paraphrases concern only reported information.

## Retrieval and boundaries

See [SOURCES.md](SOURCES.md) for verified URLs, reuse conditions, dates, coverage, and limitations. `app/resources.json` contains five short attributed paraphrases with Korean translations. Keyword scoring supplies at most two relevant passages to the model. The backend validates selected IDs and renders only local passages; no model-created citation or medical prose is used. No relevant evidence means an explicit insufficient-evidence answer.

`app/provider.py` contains the actual system-level instructions and stateless OpenAI Responses API adapter. The API key/model come from environment variables; `store:false`, bounded output, no automatic retries, and a hard request timeout are set. User/history/resource content is encoded as untrusted data. Backend response handling uses the structured selections, not unrestricted generated text. Follow-up questions come from an inspectable bilingual catalog.

## Privacy, errors, and costs

No chat database, analytics, localStorage, or file persistence. The frontend keeps at most 12 messages in tab memory and clears summaries when a new turn succeeds. Only bounded context is sent. The backend handles text transiently, does not log bodies/prompts/summaries, uses generic validation/provider errors, and sends `Cache-Control: no-store`. Start with `--no-access-log`; do not enable HTTP debug logging or prompt tracing. Infrastructure/provider logs have independent policies. Clearing a tab cannot delete prior provider requests or clipboard contents.

OpenAI processes requests under its [data policies](https://developers.openai.com/api/docs/guides/your-data). `store:false` disables Responses application-state storage, but it does **not** guarantee zero data retention. Abuse-monitoring logs may be retained, typically up to 30 days by default subject to policy exceptions/account controls. This classroom prototype is not a HIPAA service; use synthetic examples for demonstrations.

Errors are `{"detail":{"code":"..."}}`; no symptom text is echoed:

| HTTP | Codes / handling |
|---|---|
| 413 | `request_too_large` |
| 422 | `invalid_input`, including blank/oversized/unknown fields |
| 429 | `rate_limited`, `provider_rate_limited`, `daily_limit`; `Retry-After` header |
| 502 | `provider_failed`, `invalid_provider_output`; invalid/refused/incomplete output fails closed |
| 503 | `provider_not_configured` |
| 504 | `provider_timeout` |
| 500 | `internal_error` |

Frontend preserves failed drafts, disables duplicate sends, and has its own 45-second timeout. No automatic retry means fewer accidental charges.

In-memory limits are **single-process guardrails**, reset on restart and are not durable billing caps. The Render command disables forwarded-header trust, so users behind the same proxy may share one observed-address limit. Do not simply trust arbitrary `X-Forwarded-For` to improve it. For a public service add a vetted proxy configuration, authentication, shared durable limits and monitoring. Use a dedicated provider project, restricted key, provider-side model/rate controls, and spending alerts/budgets; verify whether account budget settings actually enforce a hard cap. Keep one worker and `GLOBAL_DAILY_LIMIT` low for class. Suspend the service/revoke the key after demonstration if appropriate.

## Render deployment

1. Push this **separate** repository as `careprep-backend` (no frontend or `.env`).
2. In Render, create **New → Blueprint**, connect this repository, and select `render.yaml`. Alternatively create a Python Web Service with build `pip install -r requirements.txt`, health `/health`, and start `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --no-access-log --no-proxy-headers`.
3. Set `OPENAI_API_KEY` privately in Render; leave `OPENAI_MODEL=gpt-4.1-mini` or choose a compatible account-accessible model. Set `ALLOWED_ORIGINS=https://hyjung25.github.io,http://localhost:5500,http://127.0.0.1:5500`.
4. Deploy. Copy the actual Render URL from the dashboard; do not guess its hostname. Check `/health`, then run a synthetic chat and summary to verify provider access.
5. Put that URL in the frontend's `config.js`, commit, and push. Use the deployed UI to verify CORS and all three endpoints.

A free instance may sleep and cold-start slowly; wake `/health` before recording. Free-tier availability/account requirements may differ. Render account/API access and an OpenAI key are required; no live backend deployment is claimed until the URL and provider-backed flow are tested.

## Verification

```sh
python -m pytest -q
```

An optional CI template is in `deployment/checks.example.yml`; move it into `.github/workflows/` only with suitable GitHub workflow permission.

The tests use synthetic messages and injected model/HTTP responses; they do not call a paid provider. They cover HTTP contracts, validation, CORS, missing keys, provider failure/timeout/refusal, citation integrity, summary evidence provenance and rejection of failed grounding reviews, English/Korean urgent/boundary cases, and rate limits. They are software checks, **not medical validation**, and do not measure real-model interpretation. Before submission perform a small live smoke test after credentials are configured.

For an explicitly labeled **local-only** UI fixture:

```sh
uvicorn tests.fixture_server:app --host 127.0.0.1 --port 8001 --no-access-log
```

Point frontend connection settings to `http://127.0.0.1:8001`. The UI visibly labels fixture outputs. Never deploy that module. The Render configuration runs `app.main:app` exclusively.

See [prompt_log.md](prompt_log.md) and the frontend's demo/submission documents for assignment deliverables.

## Conversation update (2026-09-27)

Follow-up replies acknowledge the current message using its exact wording (up to 400 characters; longer messages receive a brief acknowledgment). Previously rendered educational passages and already-asked catalog questions are suppressed within the bounded history. Follow-ups ask at most one new question, and new topics still receive their own retrieved passages. Relevant source links remain available. This reduces repetition while preserving the constrained medical response design. The app does not infer a symptom’s cause from volunteered context.
