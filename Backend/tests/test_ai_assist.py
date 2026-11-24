"""Travelly AI: chat/voice search assistant and help (PRD matrix 90-91, D10; owner decision 12 Nov 2026)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx
from app.services import ai_assist

from conftest import bearer
from test_ticket_holds import person
import pytest


@pytest.fixture(autouse=True)
def signed_in(client):
    """The AI is for signed-in customers (owner decision 13 Nov 2026): every call here carries a customer's token."""
    who = person(client)
    client.headers.update(bearer(who['tokens']))
    return who


TOMORROW = (datetime.now(ZoneInfo('Asia/Colombo')).date() + timedelta(days=1)).isoformat()


def turn(client, message, language='en', filters=None, asking=None):
    body = {'message': message, 'language': language, 'filters': filters or {}, **({'asking': asking} if asking else {})}
    reply = client.post('/api/v1/ai/search-assist', json=body)
    assert reply.status_code == 200, reply.text
    return reply.json()


def test_a_conversation_fills_the_hire_form_one_question_at_a_time(client):
    """No sign-in needed, nothing stored; it ends with a form to check, never a booking."""
    first = turn(client, 'naan Kandy-la irunthu Colombo pooka van venum')
    assert first['engine'] == 'rules'
    assert first['filters'] == {'pickup': 'Kandy', 'destination': 'Colombo'}
    assert first['asking'] == 'service' and {o['value'] for o in first['options']} == {'local', 'airport', 'long-distance', 'ticket'}
    step = turn(client, 'long-distance', filters=first['filters'], asking=first['asking'])
    assert step['asking'] == 'date'
    step = turn(client, 'naalai kaalai 8 mani', filters=step['filters'], asking=step['asking'])
    assert step['filters']['date'] == TOMORROW and step['filters']['time'] == '08:00' and step['asking'] == 'hours'
    step = turn(client, '10 hours', filters=step['filters'], asking=step['asking'])
    step = turn(client, '5', filters=step['filters'], asking=step['asking'])
    assert step['filters']['passengers'] == 5 and step['asking'] == 'luggage'
    done = turn(client, '2 periya bag 1 chinna', filters=step['filters'], asking=step['asking'])
    assert done['ready'] and done['asking'] is None and done['options'] == []
    assert done['filters'] == {'pickup': 'Kandy', 'destination': 'Colombo', 'service': 'long-distance', 'duration': 'ONE_DAY',
                               'date': TOMORROW, 'time': '08:00', 'hours': 10, 'passengers': 5, 'large_luggage': 2, 'small_luggage': 1}
    assert done['form_path'] == '/travel/book/details/long-distance/one-day'
    assert {row['field'] for row in done['summary']} >= {'pickup', 'destination', 'date', 'passengers'}


def test_one_sentence_in_tamil_or_sinhala_and_questions_in_that_language(client):
    ta = turn(client, 'கண்டியிலிருந்து கொழும்புக்கு நாளை காலை 7 மணி 3 பேர் டிக்கெட்', language='ta')
    assert ta['filters'] == {'service': 'ticket', 'pickup': 'Kandy', 'destination': 'Colombo', 'date': TOMORROW, 'passengers': 3}
    assert ta['ready'] and ta['form_path'] == '/travel/book/tickets' and ta['question'].startswith('உங்கள் தேடல்')
    si = turn(client, 'මහනුවර සිට කොළඹට හෙට උදේ 8ට 2 දෙනා', language='si')
    assert si['filters']['pickup'] == 'Kandy' and si['filters']['time'] == '08:00' and si['asking'] == 'service'
    assert si['question'] == ai_assist.QUESTIONS['service']['si']


def test_wrong_or_past_answers_are_asked_again_and_edits_are_kept(client):
    past = turn(client, 'yesterday 10am', filters={'service': 'local', 'pickup': 'Galle', 'destination': 'Unawatuna', 'date': '2020-01-01'})
    assert 'date' not in past['filters'] and past['asking'] == 'date'
    blank = turn(client, 'hmm', filters={'service': 'ticket'}, asking='pickup')
    assert blank['asking'] == 'pickup' and blank['notes'] == [ai_assist.NOT_UNDERSTOOD['en']]
    back = turn(client, 'return', filters={'service': 'airport', 'pickup': 'Colombo', 'destination': 'Katunayake Airport',
                                           'date': TOMORROW, 'time': '05:00'})
    assert back['filters']['journey'] == 'RETURN' and back['asking'] == 'return_date'
    rent = turn(client, 'I want a self drive rental')
    assert rent['notes'] == [ai_assist.OTHER_SERVICE['rental']['en']] and rent['asking'] is None and rent['filters']['service'] == 'rental'
    bad = client.post('/api/v1/ai/search-assist', json={'message': 'x', 'filters': {'passengers': 0}})
    assert bad.status_code == 422


def test_ai_services_answer_one_after_another_and_rules_take_over(client, monkeypatch):
    """OpenRouter first; when it fails, Groq; when every service fails, the built-in rules (owner decision 13 Nov 2026)."""
    monkeypatch.setenv('GROQ_API_KEY', 'test-groq')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-or')
    sent = []
    down = set()

    def fake(name, settings, prompt, schema, image=None):
        sent.append((name, prompt))
        if name in down:
            raise httpx.HTTPStatusError('429 limit', request=None, response=None)
        if 'help assistant' in prompt:
            return {'topic_id': 'cancel', 'answer': 'இதோ படிகள்.', 'steps': ['Bookings திறக்கவும்', 'Cancel அழுத்தவும்']}
        return {'service': 'local', 'pickup': 'Wellawatte', 'destination': 'Colombo Fort', 'passengers': 99999, 'journey': 'unknown'}
    monkeypatch.setattr(ai_assist, 'call', fake)
    reply = turn(client, 'wellawatte to fort, call me on +94 77 123 4567 or me@example.com')
    assert reply['engine'] == 'openrouter' and [n for n, _ in sent] == ['openrouter']   # the first service answered: no second call
    assert reply['filters'] == {'service': 'local', 'pickup': 'Wellawatte', 'destination': 'Colombo Fort', 'journey': 'ONE_WAY'}  # bad count dropped
    assert '+94' not in sent[0][1] and 'example.com' not in sent[0][1] and '[phone]' in sent[0][1]
    down.add('openrouter')
    sent.clear()
    helped = client.post('/api/v1/ai/help', json={'question': 'ticket eppadi cancel pannurathu', 'language': 'ta'}).json()
    assert helped['engine'] == 'groq' and [n for n, _ in sent] == ['openrouter', 'groq'] and helped['path'] == '/bookings'
    down.add('groq')
    fallback = turn(client, 'from Galle to Matara tomorrow 9am, 2 people')
    assert fallback['engine'] == 'rules' and fallback['filters']['pickup'] == 'Galle' and fallback['filters']['passengers'] == 2
    monkeypatch.setenv('AI_DAILY_LIMIT', '0')
    down.clear()
    assert turn(client, 'hello')['engine'] == 'rules'


def test_help_answers_only_from_the_guide(client):
    cancel = client.post('/api/v1/ai/help', json={'question': 'How do I cancel my ticket and get a refund?'}).json()
    assert cancel['found'] and cancel['topic_id'] == 'cancel' and cancel['path'] == '/bookings' and cancel['steps']
    tamil = client.post('/api/v1/ai/help', json={'question': 'டிக்கெட் எப்படி பதிவு செய்வது', 'language': 'ta'}).json()
    assert tamil['topic_id'] == 'book_ticket' and tamil['title'] == 'பஸ் / வேன் டிக்கெட் பதிவு' and tamil['note']
    unknown = client.post('/api/v1/ai/help', json={'question': 'what is the weather on mars', 'language': 'si'}).json()
    assert unknown['found'] is False and unknown['answer'] == ai_assist.help_guide.UNKNOWN['si'] and unknown['path'] == '/passenger/support'
    topics = client.get('/api/v1/ai/help/topics/en').json()['items']
    assert any(t['topic_id'] == 'services' for t in topics)


def test_signed_out_visitors_cannot_use_the_ai_and_each_person_has_a_daily_cap(client, monkeypatch):
    client.headers.pop('Authorization')
    assert client.post('/api/v1/ai/search-assist', json={'message': 'Kandy to Colombo'}).status_code == 401
    assert client.post('/api/v1/ai/help', json={'question': 'how to cancel'}).status_code == 401
    assert client.get('/api/v1/ai/help/topics/en').status_code == 200   # the topic list stays public
    who = person(client)
    client.headers.update(bearer(who['tokens']))
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('AI_USER_DAILY_LIMIT', '2')
    monkeypatch.setattr(ai_assist, 'call', lambda name, settings, prompt, schema, image=None: {'pickup': 'Galle'})
    engines = [turn(client, 'from Galle')['engine'] for _ in range(3)]
    assert engines == ['groq', 'groq', 'rules']   # after 2 AI answers today, the rules answer for this person
    other = person(client)
    client.headers.update(bearer(other['tokens']))
    assert turn(client, 'from Galle')['engine'] == 'groq'   # someone else still has their own quota


def test_openai_style_services_get_the_schema_then_plain_json(client, monkeypatch):
    """Groq/OpenRouter use the OpenAI chat format: JSON schema first, plain JSON if the model refuses it."""
    monkeypatch.setenv('AI_PROVIDERS', 'openrouter')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-or-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'some/model:free')
    sent = []

    class Reply:
        def __init__(self, status, payload): self.status_code, self.payload = status, payload
        def json(self): return self.payload
        def raise_for_status(self):
            if self.status_code >= 400: raise httpx.HTTPStatusError('bad', request=None, response=None)

    def fake_post(url, json=None, headers=None, timeout=None):
        import copy
        sent.append({'url': url, 'body': copy.deepcopy(json), 'auth': headers['Authorization']})
        if json['response_format']['type'] == 'json_schema':
            return Reply(400, {'error': {'message': 'structured outputs not supported'}})
        return Reply(200, {'choices': [{'message': {'content': '```json\n{"pickup": "Jaffna", "destination": "Colombo"}\n```'}}]})
    monkeypatch.setattr(ai_assist.httpx, 'post', fake_post)
    reply = turn(client, 'jaffna to colombo')
    assert reply['engine'] == 'openrouter' and reply['filters']['pickup'] == 'Jaffna' and reply['filters']['destination'] == 'Colombo'
    assert sent[0]['url'].endswith('/chat/completions') and sent[0]['body']['model'] == 'some/model:free'
    assert sent[0]['auth'] == 'Bearer test-or-key' and [x['body']['response_format']['type'] for x in sent] == ['json_schema', 'json_object']
    schema = sent[0]['body']['response_format']['json_schema']['schema']
    assert schema['type'] == 'object' and schema['properties']['service']['type'] == 'string'   # Gemini schema converted
    monkeypatch.setenv('OPENROUTER_API_KEY', '')
    assert turn(client, 'from Galle')['engine'] == 'rules'   # no key: the rules answer
