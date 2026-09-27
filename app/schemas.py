from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]
Language = Literal['en', 'ko']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Message(StrictModel):
    role: Literal['user', 'assistant']
    content: Text

class ChatRequest(StrictModel):
    message: Text
    history: list[Message] = Field(default_factory=list, max_length=12)
    language: Language = 'en'

class SummaryRequest(StrictModel):
    history: list[Message] = Field(min_length=1, max_length=12)
    language: Language = 'en'

    @model_validator(mode='after')
    def needs_user(self):
        if not any(m.role == 'user' for m in self.history):
            raise ValueError('A user message is required')
        return self

class Source(StrictModel):
    id: str
    title: str
    url: str
    retrieved_at: str
    attribution: str = 'Source: MedlinePlus, National Library of Medicine.'

class ChatResponse(StrictModel):
    response: str
    sources: list[Source]
    urgent: bool = False
    mode: Literal['ai', 'safety', 'boundary']

class SummarySection(StrictModel):
    key: str
    title: str
    notes: list[str]
    quotes: list[str]
    message_ids: list[int]

class SummaryResponse(StrictModel):
    summary: str
    sections: list[SummarySection]
    important_unknowns: list[str]
    urgent_notice: str | None = None

QuestionID = Literal['focus_clarification', 'location', 'onset', 'severity', 'progression', 'associated', 'medications', 'questions']

class ChatSelection(StrictModel):
    urgent: bool
    boundary: bool
    passage_ids: list[str] = Field(max_length=2)
    question_ids: list[QuestionID] = Field(max_length=2)

class Evidence(StrictModel):
    message_id: int
    quote: Annotated[str, StringConstraints(min_length=1, max_length=1200)]

class SummaryFact(StrictModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
    evidence: list[Evidence] = Field(min_length=1, max_length=3)

class SummarySelection(StrictModel):
    main_concern: list[SummaryFact] = Field(max_length=2)
    onset_duration: list[SummaryFact] = Field(max_length=2)
    severity_progression: list[SummaryFact] = Field(max_length=2)
    associated_symptoms: list[SummaryFact] = Field(max_length=2)
    medications_allergies: list[SummaryFact] = Field(max_length=2)
    relevant_context: list[SummaryFact] = Field(max_length=2)
    clinician_questions: list[SummaryFact] = Field(max_length=2)

class SummaryAudit(StrictModel):
    valid: bool

class UrgencyReview(StrictModel):
    decision: Literal['urgent', 'clarify_focus', 'continue']
    evidence: list[Evidence] = Field(max_length=3)
