# Knowledge base and verification record

Original pages and reuse policy inspected on **2026-09-26**. This is a small curated collection, not clinical validation. Source: MedlinePlus, National Library of Medicine. No affiliation or endorsement is implied.

| ID | Original title / URL | Included scope |
|---|---|---|
| headache | [Headache](https://medlineplus.gov/headache.html) | General causes vary; selected reasons to seek immediate help |
| cough | [Cough](https://medlineplus.gov/cough.html) | Protective reflex and duration; no medicines |
| abdominal | [Abdominal Pain](https://medlineplus.gov/abdominalpain.html) | Severity alone is insufficient; selected escalation signs |
| breathing | [Breathing Problems](https://medlineplus.gov/breathingproblems.html) | Multiple causes, some serious; professional evaluation |
| chest | [Chest Pain](https://medlineplus.gov/chestpain.html) | Persistent/crushing pain or associated symptoms require immediate care |

## Access and reuse

[MedlinePlus content policy](https://medlineplus.gov/about/using/usingcontent/) identifies **health-topic summaries** as public-domain content and requests attribution. Our short, edited paraphrases use only those summaries. We do not copy linked third-party articles, licensed A.D.A.M. encyclopedia content, images, logos, or medication monographs. No automated crawling or request-time scraping is performed. Record the date you actually review each original when updating `app/resources.json`. Do not simply advance the date without checking the source.

The `en` and `ko` passages are project-authored paraphrases/translations, not verbatim excerpts or official Korean translations. The cough passage's suggestion to record duration is a visit-preparation framing of the source's duration distinction. Korean wording and medical selection have not been independently clinically reviewed.

## Retrieval in plain language

1. Read five local JSON records at startup (IDs, titles, URLs, verification dates, keyword aliases, and passages).
2. Score each matching English/Korean topic alias: 3 for a current-message match, 1 for a user-history match. Do not use assistant history for retrieval.
3. Take at most two positive-scoring records. Supply their passages as untrusted data in the model input.
4. The model selects relevant retrieved IDs, and at most two questions from a fixed bilingual question catalog. The server rejects IDs outside the retrieved set.
5. Render the selected local passage text and construct citation metadata from local records. No model-generated clinical text or URL reaches the response. No matching/selected passage means an explicit insufficient-evidence response with no sources.

This is a lightweight retrieval-augmented, **constrained response** design: the model interprets context and selects content rather than freely writing medical advice. It needs no embedding service or vector database. It trades conversational flexibility for inspectable output. Keyword matching misses paraphrases and can return irrelevant topics. Negations and historical mentions are not understood by retrieval. The model can still choose poorly; valid source IDs do not prove relevance or medical correctness.

## Limits

The small scope is visit preparation for headache, cough, and abdominal discomfort, plus chest and breathing references. It is not a complete health encyclopedia, triage system, treatment guide, or substitute for examination. It does not cover pediatric/pregnancy-specific assessment, interactions, medication management, chronic disease management, injury images, or personalized treatment. Emergency phrase examples and model urgency selection are **not exhaustive**; both false positives and missed emergencies are possible. The lexical guard intentionally escalates even historical/negated urgent phrases rather than interpreting them as safe. Never interpret the absence of an urgent flag as reassurance.

## API implementation references

Verified 2026-09-26 against official documentation:

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs): Responses API `text.format`, strict JSON schema; refusals/incomplete output must be handled separately.
- [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini): supports structured outputs. `OPENAI_MODEL` is configurable; availability still depends on the account. No claim that this is the latest model.
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data): `store:false` does not guarantee zero retention; abuse-monitoring retention and organization settings still apply.
- [Render FastAPI deployment](https://render.com/docs/deploy-fastapi).
- [GitHub Pages publishing](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Additional implementation reference (2026-09-27)

[NHS: Sudden confusion (delirium)](https://www.nhs.uk/symptoms/confusion/) was checked while investigating a concentration-difficulty false escalation. It describes sudden confusion/disorientation and advises immediate help for sudden confusion. The app's design distinction is to clarify ambiguous task-concentration wording, not infer disorientation from it, and never use a low pain score to dismiss a separately reported urgent sign. This is an implementation inference, not a validated classification rule. No NHS content is added to the runtime corpus or copied verbatim; no UK emergency number is inferred from language.
