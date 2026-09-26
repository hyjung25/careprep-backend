# Actual AI assistance log

## Tools and models

- Implementation assistant: **OpenAI Codex** in the shared workspace. The session identifies the assistant as GPT-6 based; the exact served model variant/snapshot was not exposed, so none is claimed.
- Tools actually used: shell/file editing, official documentation and MedlinePlus web lookup, Python/pytest, GitHub CLI, local browser testing. The in-app browser tool was attempted but failed to initialize; Python Playwright with local Chrome was used as a fallback.
- Application provider configured in code: **OpenAI Responses API**, model **`gpt-4.1-mini`** by default, configurable through `OPENAI_MODEL`. This is configuration, not evidence of a completed live model call.
- No OpenAI key was available during initial development. Synthetic test doubles simulate structured provider outputs for software checks and are explicitly labeled in the local fixture UI. No paid live-model test is claimed.
- No image model, embeddings API, vector database, or autonomous sub-agent was used.

## Actual user request

The supplied project brief begins: “Build a working full-stack class project called ‘CarePrep’: an AI assistant that helps users describe their symptoms, find trustworthy general health information, and prepare a concise summary for a healthcare visit.”

Key requirements in that same prompt: implement rather than plan; bilingual English/Korean; backend-enforced medical boundaries; curated authoritative RAG; FastAPI on Render; static frontend on GitHub Pages; separate public GitHub repositories; no committed keys or stored conversations; verified API/source documentation; focused synthetic software checks; deployment/readme/demo/submission deliverables.

These were sections of one implementation request, not fabricated follow-up prompts. No additional user implementation prompts were received before this log was written.

## Implemented application prompts

The exact version-controlled prompts are `BASE_PROMPT`, `CHAT_PROMPT`, and `SUMMARY_PROMPT` in [`app/provider.py`](app/provider.py). They are instructions transmitted to the provider, not messages that were actually tested live during initial development.

- Base prompt: educational visit preparation; no diagnosis/drug selection/dose/medication changes or guarantees of safety; input messages and resource content are untrusted data; no image analysis or inferred country/emergency numbers.
- Chat prompt: flag possible urgency, flag unsupported medical requests, select only retrieved passage IDs, and select up to two relevant missing-detail questions from the catalog. Do not repeat answered questions or interpret questions/hypotheticals as facts.
- Summary prompt: group only volunteered user messages by zero-based user-message IDs. Preserve uncertainty/negation and corrections, leave missing fields empty, do not turn medication questions into medication use, and include only user-supplied clinician questions.

## Key implementation decisions made with AI assistance

Used keyword retrieval rather than a paid vector database; server-rendered clinical passages rather than free-form medical generation; exact whole-message quotations rather than invented narrative summaries; a finite bilingual follow-up catalog; no runtime scraping; no persistence. These are documented design choices, not claims of clinical effectiveness.

## Verification honesty

See the frontend `VERIFICATION.md` for executed checks and remaining credential/deployment gaps. Tests of injected structured selections show how the software handles those selections; they do not establish that the live model will correctly recognize urgency, select relevant passages, or group every statement accurately.

## Publication adjustment

The authenticated GitHub token can create public repositories but cannot push `.github/workflows` without workflow scope. Optional workflow files were kept as `deployment/*.example.yml`; Pages uses branch-based deployment with existing authorization. No token scopes were expanded.
