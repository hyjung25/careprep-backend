import json
import re
from pathlib import Path
from .schemas import Source

RESOURCES = json.loads(Path(__file__).with_name('resources.json').read_text())
BY_ID = {r['id']: r for r in RESOURCES}

QUESTIONS = {
 'location': ('Where do you feel it?', '어느 부위에 증상이 있나요?'),
 'onset': ('When did it start, and is it constant or does it come and go?', '언제 시작되었나요? 계속되나요, 아니면 나타났다 사라지나요?'),
 'severity': ('How strong does it feel in your own words, and how does it affect your day?', '본인의 표현으로 어느 정도 불편한가요? 일상에 어떤 영향을 주나요?'),
 'progression': ('Has it improved, worsened, or stayed the same?', '증상이 좋아졌나요, 심해졌나요, 아니면 비슷한가요?'),
 'associated': ('Have you noticed any other symptoms?', '함께 나타나는 다른 증상이 있나요?'),
 'medications': ('If you want to share, are there any medicines or allergies to note for your visit?', '원하시면 진료 시 참고할 복용 약이나 알레르기를 알려주세요.'),
 'questions': ('What would you like to ask the clinician?', '의료진에게 어떤 질문을 하고 싶으신가요?'),
}
FIELDS = {
 'main_concern': ('Main concern', '주요 증상'),
 'onset_duration': ('Onset and duration', '시작 시점과 지속 기간'),
 'severity_progression': ('Severity and changes', '증상의 정도와 변화'),
 'associated_symptoms': ('Associated symptoms', '동반 증상'),
 'medications_allergies': ('Medications and allergies', '복용약과 알레르기'),
 'relevant_context': ('Relevant context', '관련 상황'),
 'clinician_questions': ('Questions for the clinician', '의료진에게 할 질문'),
}

def localized(pair, language):
    return pair[language == 'ko']

def source(resource):
    return Source(**{k: resource[k] for k in ('id', 'title', 'url', 'retrieved_at')})

def retrieve(current, history):
    # Current topic has priority; only USER history can add topic context.
    def score(r):
        return sum((3 if term in current.lower() else 0) +
                   (1 if term in history.lower() else 0) for term in r['keywords'])
    return sorted((r for r in RESOURCES if score(r)), key=score, reverse=True)[:2]

# Conservative examples, NOT a comprehensive or validated triage classifier.
URGENT = re.compile(
 r"can(?:not|'t|’t) breathe|difficulty breathing|struggling to breathe|shortness of breath|"
 r"chest (?:pain|pressure)|crushing.{0,20}chest|vomit(?:ing)? blood|blood in (?:my )?stool|"
 r"worst.{0,25}headache|sudden.{0,25}(?:severe|sharp)|unconscious|passed out|"
 r"face droop|slurred speech|one.sided weakness|overdose|kill myself|suicid|"
 r"숨.{0,8}(?:못|안 쉬|어려|힘)|호흡.?곤란|가슴.{0,8}(?:통증|아파|압박)|흉통|"
 r"피.{0,5}토|혈변|의식.{0,6}(?:없|잃)|갑자기.{0,15}(?:심한|극심|마비)|자살|죽고 싶",
 re.I)
BOUNDARY = re.compile(r'diagnos|what (?:disease|illness) (?:do i|is)|dos(?:e|age)|how (?:much|many).{0,40}(?:take|pill|ibuprofen|tylenol)|(?:start|stop|change).{0,20}(?:medication|medicine)|진단|무슨 병|몇 알|몇알|용량|복용량|약.{0,10}(?:추천|끊|중단|바꿔)', re.I)

BOUNDARY_TEXT = (
 'I can help organize your concerns, but cannot diagnose, choose medicines, give doses, or advise medication changes. A clinician or pharmacist can help with medication questions.',
 '증상 정리는 도와드릴 수 있지만 진단, 약 선택, 복용량 안내, 약 변경 지시는 할 수 없습니다. 약에 관한 질문은 의료진이나 약사에게 문의하세요.')
URGENT_TEXT = (
 'What you describe may need urgent professional help. If this is happening now, seek immediate medical care or contact your local emergency service. Do not wait for this chat. I cannot assess your safety here.',
 '말씀하신 상황은 긴급한 전문적인 도움이 필요할 수 있습니다. 지금 발생하고 있다면 즉시 의료 도움을 받거나 현지 응급 서비스에 연락하세요. 이 대화를 기다리지 마세요. 여기서는 안전 여부를 판단할 수 없습니다.')
INSUFFICIENT = (
 'I do not have enough relevant information in this small resource collection to give guidance on that concern. A healthcare professional can help evaluate it. I can still help organize what you want to discuss.',
 '이 작은 자료 모음에는 해당 증상에 대해 안내할 만한 정보가 충분하지 않습니다. 의료진에게 평가를 받으세요. 진료 때 이야기할 내용은 정리해 드릴 수 있습니다.')
