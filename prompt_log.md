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

## Follow-up request: repetitive answers (2026-09-27)

The user reported “똑같은답만 나오는데” with examples of repeated source paragraphs. Updated backend rendering to suppress previously shown passages and already-asked questions, acknowledge new user wording, and limit follow-ups to one question. Updated the actual chat prompt to recognize volunteered location/timing/severity, skip already-asked questions, and avoid inferring a causal connection. Added two regression checks; 42 software checks pass. Live API credentials were subsequently configured locally (never committed); synthetic live chat and summary checks succeeded after restarting from the moved project folder.

## Summary redesign (2026-09-27)

The user called the whole-message summary unusable and showed duplicated symptom text, omitted context, and a generic advice request mislabeled as a clinician question. Replaced whole-message selection with concise per-field paraphrases carrying verbatim evidence and message IDs. Added relevant context; consolidated empty clinical categories into one missing-information line; added expandable original evidence in the UI. Added a separate grounding-review prompt that rejects unsupported facts, omitted context, lost negations, diagnoses/advice, and mislabeled clinician questions. Exact current prompts are in the backend provider module; earlier whole-message instructions in this log describe the initial implementation and are superseded.

45 synthetic backend checks passed. Two live synthetic summary checks (English and Korean) returned HTTP 200, retained volunteered context, preserved medication negation, and did not convert chatbot advice requests into clinician questions. These are software smoke tests, not medical validation or a guarantee of model accuracy. Live credentials remain only in the ignored backend `.env`.

## Urgency false-escalation report (2026-09-27)

The user showed a screenshot in which mild pain and difficulty focusing led to an urgent banner. Updated the chat prompt to distinguish ambiguous task concentration from actually reported sudden confusion without claiming safety. Removed assistant prose from model symptom history, added a user-only urgency review with verbatim evidence validation, and added a bilingual clarification question. Added regression checks for source-warning contamination, invalid urgency evidence, discarded unsupported flags, and preservation of escalation despite low pain severity. 49 software checks pass; these are not clinical validation.
