"""Travelly AI: chat/voice search assistant and help (PRD matrix 90-91, D10; owner decision 12 Nov 2026)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import httpx
from app.services import ai_assist

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
    assert rent['notes'] == [ai_assist.OTHER_SERVICE['rental']['en']] and rent['asking'] == 'service'
    bad = client.post('/api/v1/ai/search-assist', json={'message': 'x', 'filters': {'passengers': 0}})
    assert bad.status_code == 422


def test_gemini_is_used_when_configured_and_rules_take_over_when_it_fails(client, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    sent = []

    def fake(settings, prompt, schema):
        sent.append(prompt)
        if 'help assistant' in prompt:
            return {'topic_id': 'cancel', 'answer': 'இதோ படிகள்.', 'steps': ['Bookings திறக்கவும்', 'Cancel அழுத்தவும்']}
        return {'service': 'local', 'pickup': 'Wellawatte', 'destination': 'Colombo Fort', 'passengers': 99999, 'journey': 'unknown'}
    monkeypatch.setattr(ai_assist, 'gemini', fake)
    reply = turn(client, 'wellawatte to fort, call me on +94 77 123 4567 or me@example.com')
    assert reply['engine'] == 'gemini'
    assert reply['filters'] == {'service': 'local', 'pickup': 'Wellawatte', 'destination': 'Colombo Fort', 'journey': 'ONE_WAY'}  # bad count dropped
    assert '+94' not in sent[0] and 'example.com' not in sent[0] and '[phone]' in sent[0]
    helped = client.post('/api/v1/ai/help', json={'question': 'ticket eppadi cancel pannurathu', 'language': 'ta'}).json()
    assert helped['engine'] == 'gemini' and helped['path'] == '/bookings' and helped['steps_language'] == 'ta'

    def broken(settings, prompt, schema):
        raise httpx.ConnectError('offline')
    monkeypatch.setattr(ai_assist, 'gemini', broken)
    fallback = turn(client, 'from Galle to Matara tomorrow 9am, 2 people')
    assert fallback['engine'] == 'rules' and fallback['filters']['pickup'] == 'Galle' and fallback['filters']['passengers'] == 2
    monkeypatch.setenv('GEMINI_DAILY_LIMIT', '0')
    monkeypatch.setattr(ai_assist, 'gemini', fake)
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
