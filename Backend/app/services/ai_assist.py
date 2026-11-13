"""Travelly AI: talk instead of filling the search form (PRD matrix 90-91, D10), and a help assistant.

Smart search
- The person says what they need (typed or spoken, en / ta / si / Tanglish). We pull out only the fields the search
  form has, merge them with what is already known, and ask for the next missing one, one question at a time.
- Questions and the summary are fixed sentences in the person's language, written here, so the AI never invents
  wording, rules or prices.
- Nothing is booked, held or stored. When the form is complete the UI shows it for checking and editing, and the
  person presses Search, which calls the normal search endpoints, so only real, eligible vehicles appear.

Engines
- Gemini (Google AI Studio key in GEMINI_API_KEY) reads free speech best. Only the message text is sent, with email
  addresses and phone numbers masked; a daily cap protects the free tier.
- The built-in rules below always work (no key, cap reached, timeout or error).

Help
- Answers only from app/services/help_guide.py. Unknown questions get "contact Support".
"""
import json
import re
from datetime import date as Date, datetime, timedelta
from zoneinfo import ZoneInfo
import httpx
from app.core.errors import ApiError
from app.services import help_guide

ZONE = ZoneInfo('Asia/Colombo')
SERVICES = ('local', 'airport', 'long-distance', 'ticket')
HIRE = ('local', 'airport', 'long-distance')
FIELDS = ('service', 'journey', 'duration', 'pickup', 'destination', 'date', 'time', 'return_date', 'return_time',
          'hours', 'passengers', 'large_luggage', 'small_luggage', 'flight')

# ---------------------------------------------------------------------------------------------------------------
# Fixed wording (en / ta / si)

QUESTIONS = {
    'service': {'en': 'Which service do you need: Local hire, Airport hire, Long distance or a Bus/Van ticket?',
                'ta': 'எந்த சேவை வேண்டும்: உள்ளூர் வாடகை, விமான நிலையம், நீண்ட தூரம், அல்லது பஸ்/வேன் டிக்கெட்?',
                'si': 'ඔබට අවශ්‍ය සේවාව කුමක්ද: දේශීය කුලී, ගුවන්තොටුපළ, දිගු ගමන, නැත්නම් බස්/වෑන් ටිකට්?'},
    'pickup': {'en': 'Where do we pick you up?', 'ta': 'எங்கிருந்து புறப்படுகிறீர்கள்?', 'si': 'ඔබව රැගෙන යන්නේ කොහෙන්ද?'},
    'destination': {'en': 'Where are you going?', 'ta': 'எங்கே போகிறீர்கள்?', 'si': 'ඔබ යන්නේ කොහෙටද?'},
    'date': {'en': 'Which day do you travel?', 'ta': 'எந்த நாள் பயணம்?', 'si': 'ගමන් කරන්නේ කවදාද?'},
    'time': {'en': 'What time should the pickup be?', 'ta': 'எத்தனை மணிக்குப் புறப்பட வேண்டும்?', 'si': 'රැගෙන යා යුත්තේ කීයටද?'},
    'journey': {'en': 'One way or return?', 'ta': 'ஒரு வழியா, திரும்பவும் வேண்டுமா?', 'si': 'එක් පැත්තක්ද, ආපසු ගමනත් එක්කද?'},
    'return_date': {'en': 'Which day do you come back?', 'ta': 'எந்த நாள் திரும்புகிறீர்கள்?', 'si': 'ආපසු එන්නේ කවදාද?'},
    'return_time': {'en': 'What time is the return pickup?', 'ta': 'திரும்பும் போது எத்தனை மணிக்கு?', 'si': 'ආපසු රැගෙන යා යුත්තේ කීයටද?'},
    'hours': {'en': 'How many hours do you need the vehicle each day?', 'ta': 'ஒரு நாளைக்கு எத்தனை மணி நேரம் வாகனம் வேண்டும்?', 'si': 'දිනකට වාහනය පැය කීයක් අවශ්‍යද?'},
    'passengers': {'en': 'How many people are travelling?', 'ta': 'எத்தனை பேர் பயணம் செய்கிறீர்கள்?', 'si': 'ගමන් කරන්නේ කී දෙනෙක්ද?'},
    'luggage': {'en': 'How much luggage? For example "2 large, 1 small", or "no luggage".',
                'ta': 'எத்தனை பைகள்? உதாரணம் "2 பெரிய, 1 சின்ன" அல்லது "இல்லை".',
                'si': 'බඩු කීයක්ද? උදා. "ලොකු 2, පොඩි 1", නැත්නම් "නැහැ".'},
}
READY = {'en': 'Here is your search. Check it, change anything that is wrong, then press Search.',
         'ta': 'உங்கள் தேடல் இதோ. சரிபார்த்து, தவறு இருந்தால் மாற்றி, Search அழுத்துங்கள்.',
         'si': 'මෙන්න ඔබේ සෙවීම. පරීක්ෂා කර, වැරදි තිබේ නම් වෙනස් කර, Search ඔබන්න.'}
NOT_UNDERSTOOD = {'en': 'Sorry, I did not catch that.', 'ta': 'மன்னிக்கவும், புரியவில்லை.', 'si': 'සමාවෙන්න, මට තේරුණේ නැහැ.'}
PAST_TIME = {'en': 'That time has already passed.', 'ta': 'அந்த நேரம் ஏற்கனவே கடந்துவிட்டது.', 'si': 'ඒ වේලාව දැනටමත් පසු වී ඇත.'}
PAST_DATE = {'en': 'That day has already passed.', 'ta': 'அந்த நாள் ஏற்கனவே கடந்துவிட்டது.', 'si': 'ඒ දිනය දැනටමත් පසු වී ඇත.'}
RETURN_BEFORE = {'en': 'The return must be after the pickup.', 'ta': 'திரும்புவது புறப்பாட்டுக்குப் பிறகு இருக்க வேண்டும்.',
                 'si': 'ආපසු ගමන පිටත්වීමට පසුව විය යුතුයි.'}
OTHER_SERVICE = {
    'event': {'en': 'Event hire has its own form. Open Event hire to continue.', 'ta': 'நிகழ்வு வாடகைக்கு தனி படிவம் உள்ளது. Event hire-ஐத் திறக்கவும்.',
              'si': 'උත්සව කුලියට වෙනම පෝරමයක් ඇත. Event hire විවෘත කරන්න.'},
    'rental': {'en': 'Self-drive vehicle rent is not available yet. I can find a vehicle with a driver instead.',
               'ta': 'சுயமாக ஓட்டும் வாடகை இன்னும் இல்லை. ஓட்டுநருடன் வாகனம் தேடலாம்.',
               'si': 'තනියම පදවන කුලී සේවාව තවම නැහැ. රියදුරෙකු සමඟ වාහනයක් සොයා දිය හැක.'},
}
OPTIONS = {
    'service': [('local', {'en': 'Local hire', 'ta': 'உள்ளூர் வாடகை', 'si': 'දේශීය කුලී'}),
                ('airport', {'en': 'Airport hire', 'ta': 'விமான நிலையம்', 'si': 'ගුවන්තොටුපළ'}),
                ('long-distance', {'en': 'Long distance', 'ta': 'நீண்ட தூரம்', 'si': 'දිගු ගමන'}),
                ('ticket', {'en': 'Bus/Van ticket', 'ta': 'பஸ்/வேன் டிக்கெட்', 'si': 'බස්/වෑන් ටිකට්'})],
    'journey': [('ONE_WAY', {'en': 'One way', 'ta': 'ஒரு வழி', 'si': 'එක් පැත්තක්'}),
                ('RETURN', {'en': 'Return', 'ta': 'திரும்பவும்', 'si': 'ආපසු එක්ක'})],
    'luggage': [('none', {'en': 'No luggage', 'ta': 'பைகள் இல்லை', 'si': 'බඩු නැහැ'})],
}
DURATION = {'ONE_DAY': {'en': 'One day', 'ta': 'ஒரு நாள்', 'si': 'එක් දිනයක්'}, 'MULTI_DAY': {'en': 'Multi-day', 'ta': 'பல நாட்கள்', 'si': 'දින කිහිපයක්'}}
LABELS = {
    'service': {'en': 'Service', 'ta': 'சேவை', 'si': 'සේවාව'}, 'pickup': {'en': 'Pickup', 'ta': 'புறப்படும் இடம்', 'si': 'පිටත්වන තැන'},
    'destination': {'en': 'Destination', 'ta': 'போகும் இடம்', 'si': 'ගමනාන්තය'}, 'date': {'en': 'Date', 'ta': 'தேதி', 'si': 'දිනය'},
    'time': {'en': 'Pickup time', 'ta': 'நேரம்', 'si': 'වේලාව'}, 'journey': {'en': 'Journey', 'ta': 'பயணம்', 'si': 'ගමන'},
    'return_date': {'en': 'Return date', 'ta': 'திரும்பும் தேதி', 'si': 'ආපසු දිනය'}, 'return_time': {'en': 'Return time', 'ta': 'திரும்பும் நேரம்', 'si': 'ආපසු වේලාව'},
    'hours': {'en': 'Hours per day', 'ta': 'நாளுக்கு மணி நேரம்', 'si': 'දිනකට පැය'}, 'passengers': {'en': 'Travellers', 'ta': 'பயணிகள்', 'si': 'මගීන්'},
    'large_luggage': {'en': 'Large luggage', 'ta': 'பெரிய பைகள்', 'si': 'ලොකු බඩු'}, 'small_luggage': {'en': 'Small luggage', 'ta': 'சின்ன பைகள்', 'si': 'පොඩි බඩු'},
    'flight': {'en': 'Flight', 'ta': 'விமானம்', 'si': 'ගුවන් ගමන'}, 'duration': {'en': 'Trip length', 'ta': 'பயண நீளம்', 'si': 'ගමනේ දිග'},
}


def say(table, language):
    return table.get(language) or table['en']


# ---------------------------------------------------------------------------------------------------------------
# Built-in rules (always available)

WORDS = lambda *w: '(?:' + '|'.join(w) + ')'
TODAY = WORDS('today', 'tonight', 'inru', 'indru', 'indaikku', 'innaikku', 'இன்று', 'இன்னைக்கு', 'இன்றைக்கு', 'අද')
AFTER = WORDS('day after tomorrow', 'naalai marunaal', 'nalai maru naal', 'naalai maru naal', 'நாளை மறுநாள்', 'අනිද්දා')
TOMORROW = WORDS('tomorrow', 'tmrw', 'naalai', 'nalai', 'naalaikku', 'nalaikku', 'naalaiku', 'நாளை', 'நாளைக்கு', 'හෙට')
MORNING = WORDS('am', 'morning', 'kaalai', 'kalai', 'காலை', 'උදේ', 'උදෑසන')
LATER = WORDS('pm', 'evening', 'afternoon', 'night', 'maalai', 'malai', 'saayangaalam', 'sayangalam', 'madhiyam', 'mathiyam',
              'iravu', 'மாலை', 'சாயங்காலம்', 'மதியம்', 'இரவு', 'හවස', 'රෑ', 'දවල්')
MONTHS = {m: i + 1 for i, names in enumerate([
    ('jan', 'january'), ('feb', 'february'), ('mar', 'march'), ('apr', 'april'), ('may',), ('jun', 'june'), ('jul', 'july'),
    ('aug', 'august'), ('sep', 'sept', 'september'), ('oct', 'october'), ('nov', 'november'), ('dec', 'december')]) for m in names}
WEEKDAYS = {d: i for i, names in enumerate([('monday', 'mon', 'thingal', 'திங்கள்', 'සඳුදා'), ('tuesday', 'tue', 'sevvai', 'செவ்வாய்', 'අඟහරුවාදා'),
            ('wednesday', 'wed', 'budhan', 'புதன்', 'බදාදා'), ('thursday', 'thu', 'vyazhan', 'வியாழன்', 'බ්‍රහස්පතින්දා'),
            ('friday', 'fri', 'velli', 'வெள்ளி', 'සිකුරාදා'), ('saturday', 'sat', 'sani', 'சனி', 'සෙනසුරාදා'),
            ('sunday', 'sun', 'nyayiru', 'ஞாயிறு', 'ඉරිදා')]) for d in names}
PEOPLE = WORDS('people', 'persons', 'person', 'passengers', 'passenger', 'pax', 'adults', 'travellers', 'travelers', 'members',
               'peru', 'per', 'pear', 'paer', 'பேர்', 'பேரு', 'நபர்', 'දෙනා', 'දෙනෙක්', 'දෙනෙකු')
ALONE = WORDS('just me', 'only me', 'alone', 'myself', 'naan mattum', 'nan mattum', 'naan thaniya', 'thaniya', 'நான் மட்டும்', 'தனியா', 'මම විතරයි', 'මම තනියම')
BAG = WORDS('bags?', 'luggage', 'suitcases?', 'baggage', 'pai', 'பை', 'பைகள்', 'බෑග්', 'බඩු')
LARGE = WORDS('large', 'big', 'periya', 'peria', 'பெரிய', 'ලොකු')
SMALL = WORDS('small', 'hand', 'chinna', 'sinna', 'சின்ன', 'சிறிய', 'පොඩි')
NONE = WORDS('no luggage', 'no bags?', 'without luggage', 'luggage illa', 'bag illa', 'bags illa', 'pai illa', 'illa', 'illai', 'none',
             'nothing', 'no', 'zero', 'இல்லை', 'இல்ல', 'නැහැ', 'නෑ', 'බඩු නැහැ')
FILLER = re.compile(r'\b(?:i|we|need|want|a|an|the|van|car|bus|vehicle|cab|taxi|please|pls|book|go|going|travel|venum|vendum|'
                    r'naan|nan|enakku|ennakku|pooka|poga|ponum|pogonum|poganum|pokanum|irunthu|irundhu|start|from|to|my|is|at|'
                    r'for|pickup|pick|up|me|us|ok|okay|yes|place|location|city|ticket|tickets|seat|seats|la|kku|ku|hmm+|hello|hi|hey|what|sorry|no|illa|aama|aamaa|thanks|thank|you)\b', re.I)
PLACE_STOP = r'(?=\s+(?:on|at|by|tomorrow|today|tonight|for|with|from|to|and|naalai|nalai|indaikku|kaalai|maalai|\d)\b|[,.!?]|$)'


# Common places written in Tamil or Sinhala, so the place search (English names) finds them. Gemini handles others.
PLACE_NAMES = {
    'கொழும்பு': 'Colombo', 'கண்டி': 'Kandy', 'காலி': 'Galle', 'யாழ்ப்பாணம்': 'Jaffna', 'திருகோணமலை': 'Trincomalee',
    'மட்டக்களப்பு': 'Batticaloa', 'நுவரெலியா': 'Nuwara Eliya', 'அனுராதபுரம்': 'Anuradhapura', 'வவுனியா': 'Vavuniya',
    'நீர்கொழும்பு': 'Negombo', 'கட்டுநாயக்க': 'Katunayake', 'எல்ல': 'Ella', 'பதுளை': 'Badulla', 'மன்னார்': 'Mannar',
    'கிளிநொச்சி': 'Kilinochchi', 'புத்தளம்': 'Puttalam', 'குருநாகல்': 'Kurunegala', 'மாத்தறை': 'Matara', 'அம்பாறை': 'Ampara',
    'කොළඹ': 'Colombo', 'මහනුවර': 'Kandy', 'නුවර': 'Kandy', 'ගාල්ල': 'Galle', 'යාපනය': 'Jaffna', 'ත්‍රිකුණාමලය': 'Trincomalee',
    'මඩකලපුව': 'Batticaloa', 'නුවරඑළිය': 'Nuwara Eliya', 'අනුරාධපුරය': 'Anuradhapura', 'මීගමුව': 'Negombo', 'කටුනායක': 'Katunayake',
    'ඇල්ල': 'Ella', 'බදුල්ල': 'Badulla', 'කුරුණෑගල': 'Kurunegala', 'මාතර': 'Matara', 'වවුනියාව': 'Vavuniya', 'දඹුල්ල': 'Dambulla',
    'සීගිරිය': 'Sigiriya', 'හම්බන්තොට': 'Hambantota', 'රත්නපුර': 'Ratnapura', 'පොළොන්නරුව': 'Polonnaruwa',
}


def clean_place(text):
    text = text.strip()
    if text in PLACE_NAMES: return PLACE_NAMES[text]
    text = re.sub(r'\s+', ' ', FILLER.sub(' ', text)).strip(' ,.-!?')
    return text[:100].strip().title() if len(text) >= 2 else None


def next_weekday(today, index):
    ahead = (index - today.weekday()) % 7
    return today + timedelta(days=ahead or 7)


def find_date(text, today):
    if re.search(AFTER, text): return today + timedelta(days=2)
    if re.search(TOMORROW, text): return today + timedelta(days=1)
    if re.search(TODAY, text): return today
    if m := re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', text):
        return safe_date(int(m[1]), int(m[2]), int(m[3]))
    if m := re.search(r'\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b', text):
        year = int(m[3]) if m[3] else today.year
        found = safe_date(year + 2000 if year < 100 else year, int(m[2]), int(m[1]))
        return roll_year(found, today, bool(m[3]))
    month_names = '|'.join(sorted(MONTHS, key=len, reverse=True))
    if m := re.search(rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\b', text) or \
            re.search(rf'\b({month_names})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b', text):
        day, month = (m[1], m[2]) if m[1].isdigit() else (m[2], m[1])
        return roll_year(safe_date(today.year, MONTHS[month], int(day)), today, False)
    for name, index in sorted(WEEKDAYS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf'(?<![\w஀-෿]){re.escape(name)}(?![a-z])', text):
            return next_weekday(today, index)
    return None


def safe_date(y, m, d):
    try:
        return Date(y, m, d)
    except ValueError:
        return None


def roll_year(found, today, year_given):
    if found and not year_given and found < today:
        return safe_date(found.year + 1, found.month, found.day)
    return found


HINT = f'({MORNING[3:-1]}|{LATER[3:-1]})'
CLOCK = r"(?:mani|maniku|manikku|o'?clock|மணி|மணிக்கு)"


def find_time(text, bare=False):
    """"8:30", "8.30 pm", "8am", "kaalai 8 mani", "8 mani", "saayangaalam 5", "8ට". A bare "8" only answers a time question."""
    hour = minute = hint = None
    if m := re.search(r'\b(\d{1,2})[:.](\d{2})\b\s*' + HINT + '?', text):
        hour, minute, hint = int(m[1]), int(m[2]), m[3]
    elif m := re.search(r'(?<![a-z])' + HINT + r'\s*(\d{1,2})(?:[:.](\d{2}))?\b', text):
        hint, hour, minute = m[1], int(m[2]), int(m[3] or 0)
    elif m := re.search(r'\b(\d{1,2})\s*(?:' + CLOCK + r'\s*)?' + HINT + r'(?![a-z])', text):
        hour, minute, hint = int(m[1]), 0, m[2]
    elif m := re.search(r'\b(\d{1,2})\s*' + CLOCK, text) or re.search(r'(\d{1,2})\s*ට', text):
        hour, minute = int(m[1]), 0
    elif bare and (m := re.fullmatch(r'\s*(\d{1,2})\s*', text)):
        hour, minute = int(m[1]), 0
    if hour is None:
        return None
    if hint and re.fullmatch(LATER, hint) and hour < 12: hour += 12
    if hint and re.fullmatch(MORNING, hint) and hour == 12: hour = 0
    return f'{hour:02d}:{minute:02d}' if 0 <= hour <= 23 and 0 <= minute <= 59 else None


def find_places(raw):
    pickup = destination = None
    text = raw.strip()
    if m := re.search(r'\bfrom\s+(.+?)\s+to\s+(.+?)' + PLACE_STOP, text, re.I):
        pickup, destination = m[1], m[2]
    else:
        if m := re.search(r'\bfrom\s+(.+?)' + PLACE_STOP, text, re.I): pickup = m[1]
        if m := re.search(r'\bto\s+(.+?)' + PLACE_STOP, text, re.I): destination = m[1]
    # Tanglish: "kandy-la irunthu colombo-kku", "colombo pooka"
    if m := re.search(r'([\w ]+?)[- ]?(?:la|le|il|lla)\s+(?:irunthu|irundhu|irunchu|start)', text, re.I): pickup = m[1]
    if m := re.search(r'([\w]+(?: [\w]+)?)[- ](?:kku|ku|ukku)\b', text, re.I): destination = m[1]
    elif m := re.search(r'([\w]+(?: [\w]+)?)\s+(?:pooka|poga|ponum|pogonum|poganum|pokanum|pogha)\b', text, re.I): destination = m[1]
    # Tamil script: "கண்டியிலிருந்து கொழும்புக்கு"
    if m := re.search(r'([஀-௿]+?)(?:யிலிருந்து|இலிருந்து|லிருந்து|ிலிருந்து|ல இருந்து)', text): pickup = m[1]
    if m := re.search(r'([஀-௿]+?)க்கு(?![஀-௿])', text): destination = m[1]
    # Sinhala: "මහනුවර සිට කොළඹට"
    if m := re.search(r'([඀-෿]+)\s+(?:සිට|ඉඳන්|ඉදන්)', text): pickup = m[1]
    for word in re.findall(r'[඀-෿]+ට(?![඀-෿])', text):
        if word not in ('සිට', 'හෙට', 'කීයට', 'වෙලාවට', 'උදේට', 'හවසට', 'රෑට'):
            destination = word[:-1]
            break
    return (clean_place(pickup) if pickup else None), (clean_place(destination) if destination else None)


def rules(message, asking, known, today):
    """Pull form fields out of one message. `asking` is the field we just asked, so a bare answer fits it."""
    text = ' '.join(message.lower().split())
    found = {}
    if re.search(r'\b(?:airport|katunayake|bia|cmb|mattala)\b|விமான|ගුවන්', text): found['service'] = 'airport'
    elif re.search(r'\b(?:ticket|tickets|seat|seats)\b|டிக்கெட்|இருக்கை|ටිකට්|ආසන', text): found['service'] = 'ticket'
    elif re.search(r'\b(?:long distance|long trip|tour|multi[- ]?day|round tour)\b|நீண்ட|දිගු', text): found['service'] = 'long-distance'
    elif re.search(r'\b(?:local|town|city|nearby)\b|உள்ளூர்|දේශීය', text): found['service'] = 'local'
    elif re.search(r'\b(?:event|wedding|function|kalyanam)\b|திருமண|විවාහ|උත්සව', text): found['service'] = 'event'
    elif re.search(r'\b(?:rent|rental|self[- ]?drive)\b', text): found['service'] = 'rental'
    if asking == 'service' and 'service' not in found:
        for value, names in OPTIONS['service']:
            if any(n.lower() in text for n in names.values()) or text.strip() == value: found['service'] = value
    if re.search(r'\b(?:return|round trip|two way|come back|back again|thirumba|thirumbi)\b|திரும்ப|ආපසු', text): found['journey'] = 'RETURN'
    elif re.search(r'\b(?:one way|oneway|single)\b|ஒரு வழி|එක් පැත්ත', text): found['journey'] = 'ONE_WAY'
    if m := re.search(r'\b(\d{1,2})\s*(?:days|day|naal|naatkal)\b|(\d{1,2})\s*(?:நாள்|நாட்கள்|දින)', text):
        days = int(m[1] or m[2])
        if days > 1: found['duration'], found['days'] = 'MULTI_DAY', days
    if m := re.search(r'\b(\d{1,2})\s*(?:hours|hour|hrs|hr|mani neram)\b|(\d{1,2})\s*(?:மணி நேரம்|පැය)', text):
        found['hours'] = int(m[1] or m[2]); text = text.replace(m[0], ' ')
    if m := re.search(rf'\b(\d{{1,3}})\s*{PEOPLE}(?![a-z])', text):
        found['passengers'] = int(m[1]); text = text.replace(m[0], ' ')
    elif re.search(ALONE, text): found['passengers'] = 1
    elif asking == 'passengers' and (m := re.fullmatch(r'\s*(\d{1,3})\s*', text)): found['passengers'] = int(m[1])
    large = re.search(rf'(\d{{1,3}})\s*{LARGE}(?:\s*{BAG})?', text) or re.search(rf'{LARGE}\s*{BAG}?\s*(\d{{1,3}})', text)
    small = re.search(rf'(\d{{1,3}})\s*{SMALL}(?:\s*{BAG})?', text) or re.search(rf'{SMALL}\s*{BAG}?\s*(\d{{1,3}})', text)
    plain = re.search(rf'(\d{{1,3}})\s*{BAG}', text)
    if large or small or plain:
        found['large_luggage'] = int(large[1]) if large else (int(plain[1]) if plain and not small else 0)
        found['small_luggage'] = int(small[1]) if small else 0
        for m in (large, small, plain):
            if m: text = text.replace(m[0], ' ')
    elif asking == 'luggage' and (re.search(rf'(?<![\w஀-෿]){NONE}(?![a-z])', text) or text.strip() == 'none'):
        found['large_luggage'] = found['small_luggage'] = 0
    elif asking == 'luggage' and (m := re.fullmatch(r'\s*(\d{1,3})\s*', text)):
        found['large_luggage'], found['small_luggage'] = int(m[1]), 0
    if (day := find_date(text, today)):
        found['return_date' if asking == 'return_date' else 'date'] = day.isoformat()
    when = find_time(text, bare=asking in ('time', 'return_time'))
    if when:
        found['return_time' if asking == 'return_time' else 'time'] = when
    if m := re.search(r'\b([a-z]{2}\s?\d{2,4})\b', text) if known.get('service') == 'airport' or found.get('service') == 'airport' else None:
        if re.search(r'\bflight\b', text): found['flight'] = m[1].upper().replace(' ', '')
    pickup, destination = find_places(message)
    if asking in ('pickup', 'destination') and not (pickup or destination):
        leftover = re.sub(rf'{TODAY}|{TOMORROW}|\d+', ' ', message, flags=re.I)
        value = clean_place(leftover)
        if value: found[asking] = value
    if pickup: found['pickup'] = pickup
    if destination: found['destination'] = destination
    return found


# ---------------------------------------------------------------------------------------------------------------
# Gemini (optional)

MASK = [(re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+'), '[email]'), (re.compile(r'\+?\d[\d\s-]{8,}\d'), '[phone]')]


def masked(text):
    for pattern, replacement in MASK:
        text = pattern.sub(replacement, text)
    return text


KEYS = {'groq': 'groq_api_key', 'openrouter': 'openrouter_api_key', 'gemini': 'gemini_api_key'}


def providers(settings, vision=False):
    """The AI services to try, in order, that have a key (AI_PROVIDERS / AI_VISION_PROVIDERS)."""
    order = settings.ai_vision_providers if vision else settings.ai_providers
    names = [n.strip().lower() for n in (order or '').split(',') if n.strip()]
    return [n for n in dict.fromkeys(names) if n in KEYS and getattr(settings, KEYS[n]).strip()
            and not (vision and n == 'groq')]


def call(name, settings, prompt, schema, image=None):
    """One JSON answer from one service. `image` is a data URL (odometer photo)."""
    if name == 'gemini':
        parts = [{'text': prompt}]
        if image:
            mime, data = image[5:].split(';base64,', 1)
            parts.insert(0, {'inlineData': {'mimeType': mime, 'data': data}})
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent'
        body = {'contents': [{'role': 'user', 'parts': parts}],
                'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'responseSchema': schema}}
        reply = httpx.post(url, json=body, headers={'x-goog-api-key': settings.gemini_api_key}, timeout=timeout(settings, image))
        reply.raise_for_status()
        return json.loads(reply.json()['candidates'][0]['content']['parts'][0]['text'])
    if name == 'groq':
        return openai_style(settings.groq_base_url, settings.groq_api_key, settings.groq_model, settings, prompt, schema, image)
    model = settings.openrouter_vision_model if image else settings.openrouter_model
    return openai_style(settings.openrouter_base_url, settings.openrouter_api_key, model, settings, prompt, schema, image)


def timeout(settings, image):
    return max(settings.ai_timeout_seconds, 20 if image else 0)


def ask(settings, prompt, schema, image=None):
    """Try each service in order; the first good answer wins. Returns (data, service name)."""
    for name in providers(settings, vision=bool(image)):
        try:
            return call(name, settings, prompt, schema, image), name
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
            continue   # limit reached, model gone, bad reply: try the next service
    raise ValueError('no AI service answered')


def json_schema(schema):
    """Gemini-style schema (OBJECT, STRING, ...) -> standard JSON Schema for OpenAI-style services."""
    out = {'type': schema['type'].lower()}
    if 'enum' in schema: out['enum'] = schema['enum']
    if 'properties' in schema:
        out['properties'] = {k: json_schema(v) for k, v in schema['properties'].items()}
        out['additionalProperties'] = False
    if 'items' in schema: out['items'] = json_schema(schema['items'])
    if 'required' in schema: out['required'] = schema['required']
    return out


def json_text(text):
    """The JSON object in a model's reply, also when it is wrapped in ```json fences or a sentence."""
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.strip('`')
        text = text[4:] if text.lower().startswith('json') else text
    first, last = text.find('{'), text.rfind('}')
    if first < 0 or last < first:
        raise ValueError('no JSON in the reply')
    return json.loads(text[first:last + 1])


def openai_style(base_url, key, model, settings, prompt, schema, image=None):
    """Groq and OpenRouter (OpenAI chat-completions format). Asks for the JSON schema; if the model does not support
    structured output, asks again for plain JSON."""
    content = [{'type': 'text', 'text': prompt + ' Reply with one JSON object only.'}]
    if image:
        content.insert(0, {'type': 'image_url', 'image_url': {'url': image}})
    body = {'model': model, 'temperature': 0, 'messages': [{'role': 'user', 'content': content if image else content[0]['text']}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'answer', 'strict': False, 'schema': json_schema(schema)}}}
    headers = {'Authorization': f'Bearer {key}', 'X-Title': 'Travelly'}
    url = base_url.rstrip('/') + '/chat/completions'
    reply = httpx.post(url, json=body, headers=headers, timeout=timeout(settings, image))
    if reply.status_code in (400, 404, 422):   # no structured output on this model: plain JSON mode
        body['response_format'] = {'type': 'json_object'}
        reply = httpx.post(url, json=body, headers=headers, timeout=timeout(settings, image))
    reply.raise_for_status()
    data = reply.json()
    if data.get('error'):
        raise ValueError(str(data['error'])[:200])
    return json_text(data['choices'][0]['message']['content'])


def ai_allowed(store, settings, user_id=None, vision=False):
    """Use the AI services only while the free quotas last: a cap per person (AI is for signed-in customers, owner
    decision 13 Nov 2026) and a cap for the whole site. Past either cap, or with no key, the built-in rules answer."""
    if not providers(settings, vision) or settings.ai_daily_limit <= 0:
        return False
    try:
        if user_id is not None:
            if settings.ai_user_daily_limit <= 0:
                return False
            store.rate(f'ai-user:{user_id}', settings.ai_user_daily_limit, 86400)
        store.rate('ai-daily', settings.ai_daily_limit, 86400)
        return True
    except ApiError:
        return False


EXTRACT_SCHEMA = {'type': 'OBJECT', 'properties': {
    'service': {'type': 'STRING', 'enum': ['local', 'airport', 'long-distance', 'ticket', 'event', 'rental', 'unknown']},
    'journey': {'type': 'STRING', 'enum': ['ONE_WAY', 'RETURN', 'unknown']},
    'duration': {'type': 'STRING', 'enum': ['ONE_DAY', 'MULTI_DAY', 'unknown']},
    'days': {'type': 'INTEGER'}, 'pickup': {'type': 'STRING'}, 'destination': {'type': 'STRING'},
    'date': {'type': 'STRING'}, 'time': {'type': 'STRING'}, 'return_date': {'type': 'STRING'}, 'return_time': {'type': 'STRING'},
    'hours': {'type': 'INTEGER'}, 'passengers': {'type': 'INTEGER'}, 'large_luggage': {'type': 'INTEGER'},
    'small_luggage': {'type': 'INTEGER'}, 'flight': {'type': 'STRING'}}}


def gemini_extract(settings, message, asking, known, now):
    prompt = (
        'You read one message from a traveller in Sri Lanka (English, Tamil, Sinhala or Tamil/Sinhala written in English letters) '
        'and fill a vehicle search form. Return JSON with ONLY the fields the message states or clearly implies; omit the rest. '
        'Never guess a field the message does not give. Places: the place name as said, in English letters if you can '
        '(for example கொழும்பு -> Colombo). Dates as YYYY-MM-DD, times as 24-hour HH:MM. '
        'service: local = within a town/area, airport = to or from an airport, long-distance = between cities or a tour, '
        'ticket = a seat on a scheduled bus or van, event = a wedding or event with several vehicles, rental = self-drive. '
        'A bare answer (a number, a place, a time) answers the question being asked. '
        f'Now in Sri Lanka: {now:%A %Y-%m-%d %H:%M}. Question being asked: {asking or "none"}. '
        f'Already known: {json.dumps(known, ensure_ascii=False)}. Message: {masked(message)}')
    data, engine = ask(settings, prompt, EXTRACT_SCHEMA)
    return {k: v for k, v in data.items() if v not in (None, '', 'unknown')}, engine


# ---------------------------------------------------------------------------------------------------------------
# Merge, check and ask

def as_int(value, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def tidy(found, filters, today):  # noqa: C901 - one check per form field
    """Keep only valid values for form fields; return (filters, problem message or None, field to ask again)."""
    out, problem, again = {}, None, None
    if filters:   # what the UI sends back is checked again too (a date can pass while the chat is open)
        out, problem, again = tidy(filters, {}, today)
    for key, value in found.items():
        if key == 'service' and value in SERVICES + ('event', 'rental'): out['service'] = value
        elif key == 'journey' and value in ('ONE_WAY', 'RETURN'): out['journey'] = value
        elif key == 'duration' and value in ('ONE_DAY', 'MULTI_DAY'): out['duration'] = value
        elif key in ('pickup', 'destination') and isinstance(value, str) and 2 <= len(value.strip()) <= 100:
            out[key] = value.strip()
        elif key in ('date', 'return_date'):
            day = safe_iso(value)
            if day is None: continue
            if day < today: problem, again = PAST_DATE, key; continue
            if day > today + timedelta(days=365): continue
            out[key] = day.isoformat()
        elif key in ('time', 'return_time') and isinstance(value, str) and re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
            out[key] = value
        elif key == 'hours' and (n := as_int(value, 1, 24)): out['hours'] = n
        elif key == 'passengers' and (n := as_int(value, 1, 200)): out['passengers'] = n
        elif key in ('large_luggage', 'small_luggage') and (n := as_int(value, 0, 200)) is not None: out[key] = n
        elif key == 'flight' and isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9 -]{2,24}', value): out['flight'] = value.upper()
    if 'large_luggage' in out and 'small_luggage' not in out: out['small_luggage'] = 0
    if 'small_luggage' in out and 'large_luggage' not in out: out['large_luggage'] = 0
    if found.get('days') and out.get('date') and as_int(found['days'], 2, 30):
        out['duration'] = 'MULTI_DAY'
        out['return_date'] = (Date.fromisoformat(out['date']) + timedelta(days=int(found['days']) - 1)).isoformat()
    if out.get('service') == 'long-distance' and out.get('journey'):
        out.pop('journey')
    if out.get('service') == 'ticket':
        for k in ('journey', 'duration', 'time', 'return_date', 'return_time', 'hours', 'large_luggage', 'small_luggage', 'flight'):
            out.pop(k, None)
    if out.get('service') != 'airport': out.pop('flight', None)
    return out, problem, again


def safe_iso(value):
    try:
        return Date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def still_needed(f, now):
    service = f.get('service')
    order = ['service', 'pickup', 'destination', 'date']
    if service == 'ticket':
        return [x for x in order + ['passengers'] if x not in f]
    order.append('time')
    if service in ('local', 'airport') and f.get('journey') == 'RETURN':
        order += ['return_date', 'return_time']
    if service == 'long-distance':
        order.append('hours')
        if f.get('duration') == 'MULTI_DAY': order.append('return_date')
    order += ['passengers', 'luggage']
    missing = [x for x in order if (x != 'luggage' and x not in f) or (x == 'luggage' and 'large_luggage' not in f)]
    return missing


def timing_problem(f, now):
    if f.get('date') and f.get('time'):
        start = datetime.fromisoformat(f'{f["date"]}T{f["time"]}').replace(tzinfo=ZONE)
        if start <= now: return PAST_TIME, 'time'
        if f.get('return_date'):
            back = datetime.fromisoformat(f'{f["return_date"]}T{f.get("return_time") or "23:59"}').replace(tzinfo=ZONE)
            if back <= start: return RETURN_BEFORE, 'return_date'
    return None, None


def form_path(f):
    service = f.get('service')
    if service == 'ticket': return '/travel/book/tickets'
    if service == 'long-distance':
        return '/travel/book/details/long-distance/' + ('multi-day' if f.get('duration') == 'MULTI_DAY' else 'one-day')
    if service in ('local', 'airport'): return f'/travel/book/details/{service}'
    if service == 'event': return '/travel/book/event'
    return '/travel/book/service'


def summary(f, language):
    names = dict(OPTIONS['service'])
    rows = []
    for key in ('service', 'pickup', 'destination', 'date', 'time', 'journey', 'duration', 'return_date', 'return_time', 'hours',
                'passengers', 'large_luggage', 'small_luggage', 'flight'):
        if key in f:
            value = f[key]
            if key == 'service' and value in names: value = say(names[value], language)
            if key == 'journey': value = say(dict(OPTIONS['journey'])[value], language)
            if key == 'duration': value = say(DURATION[value], language)
            rows.append({'field': key, 'label': say(LABELS[key], language), 'value': str(value)})
    return rows


def search_assist(settings, store, message, language, filters, asking, now=None, user_id=None):
    now = now or datetime.now(ZONE)
    today = now.date()
    engine = 'rules'
    found = None
    if ai_allowed(store, settings, user_id):
        try:
            found, engine = gemini_extract(settings, message, asking, filters, now)
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
            found = None
    if found is None:
        found = rules(message, asking, filters, today)
    merged, problem, again = tidy(found, filters, today)
    if not problem:
        problem, again = timing_problem(merged, now)
        if again: merged.pop(again, None)
    understood = bool(set(merged.items()) - set((k, v) for k, v in filters.items()))
    if merged.get('service') in ('event', 'rental'):
        kind = merged['service']
        if kind == 'rental': merged.pop('service')
        return response(merged, language, engine, notes=[say(OTHER_SERVICE[kind], language)],
                        asking=None if kind == 'event' else 'service', ready=kind == 'event')
    if merged.get('service') in ('local', 'airport'): merged.setdefault('journey', 'ONE_WAY')   # the form's default; editable
    if merged.get('service') == 'long-distance': merged.setdefault('duration', 'ONE_DAY')
    missing = still_needed(merged, now)
    if again and again not in missing: missing.insert(0, again)
    notes = [say(problem, language)] if problem else ([] if understood or not message.strip() else [say(NOT_UNDERSTOOD, language)])
    return response(merged, language, engine, notes=notes, asking=missing[0] if missing else None, ready=not missing)


def response(f, language, engine, notes, asking, ready):
    question = say(READY, language) if ready else say(QUESTIONS[asking], language)
    return {'filters': f, 'asking': None if ready else asking, 'question': question, 'notes': notes,
            'options': [{'value': v, 'label': say(names, language)} for v, names in OPTIONS.get(asking or '', [])] if not ready else [],
            'ready': ready, 'form_path': form_path(f), 'summary': summary(f, language), 'language': language, 'engine': engine}


# ---------------------------------------------------------------------------------------------------------------
# Help

HELP_SCHEMA = {'type': 'OBJECT', 'properties': {
    'topic_id': {'type': 'STRING'}, 'answer': {'type': 'STRING'}, 'steps': {'type': 'ARRAY', 'items': {'type': 'STRING'}}},
    'required': ['topic_id', 'answer', 'steps']}
LANGUAGE_NAMES = {'en': 'English', 'ta': 'Tamil (Tamil script)', 'si': 'Sinhala (Sinhala script)'}


def match_topics(question):
    text = ' '.join(question.lower().split())
    scored = []
    for topic in help_guide.TOPICS:
        score = sum(len(k) for k in topic['keywords'] if k in text)
        if score: scored.append((score, topic))
    scored.sort(key=lambda pair: -pair[0])
    return [t for _, t in scored]


def topic_out(topic, language, steps=None, answer=None, engine='rules'):
    note = help_guide.STEPS_IN_ENGLISH.get(language) if steps is None else None
    return {'found': True, 'topic_id': topic['id'], 'title': say(topic['title'], language), 'answer': answer,
            'steps': steps or topic['steps'], 'steps_language': language if steps else 'en', 'note': note,
            'path': topic['path'], 'related': [], 'language': language, 'engine': engine}


def unknown(language, engine):
    support = help_guide.BY_ID['support']
    return {'found': False, 'topic_id': None, 'title': None, 'answer': say(help_guide.UNKNOWN, language), 'steps': [],
            'steps_language': language, 'note': None, 'path': support['path'], 'related': [], 'language': language, 'engine': engine}


def help_answer(settings, store, question, language, user_id=None):
    candidates = match_topics(question)
    if ai_allowed(store, settings, user_id):
        guide = [{'id': t['id'], 'title': t['title']['en'], 'steps': t['steps']} for t in help_guide.TOPICS]
        prompt = (
            'You are the help assistant of Travelly, a Sri Lankan vehicle hire and ticket app. Answer ONLY from the guide '
            'below. Pick the one topic that answers the question and give its steps, rewritten simply in '
            f'{LANGUAGE_NAMES[language]}, without adding any rule, price, time limit or feature that is not in the guide. '
            'If no topic answers it, return topic_id "none", an empty answer and no steps. '
            'answer = one short sentence. '
            f'Guide: {json.dumps(guide, ensure_ascii=False)} Question: {masked(question)}')
        try:
            data, engine = ask(settings, prompt, HELP_SCHEMA)
            topic = help_guide.BY_ID.get(data.get('topic_id'))
            if topic is None:
                return unknown(language, engine)
            steps = [str(s)[:400] for s in data.get('steps') or []][:8] or None
            out = topic_out(topic, language, steps=steps, answer=str(data.get('answer') or '')[:400] or None, engine=engine)
            out['related'] = related(candidates, topic, language)
            return out
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
            pass
    if not candidates:
        return unknown(language, 'rules')
    out = topic_out(candidates[0], language)
    out['related'] = related(candidates, candidates[0], language)
    return out


def related(candidates, chosen, language):
    return [{'topic_id': t['id'], 'title': say(t['title'], language), 'path': t['path']} for t in candidates if t is not chosen][:3]


def topics(language):
    return [{'topic_id': t['id'], 'title': say(t['title'], language), 'path': t['path']} for t in help_guide.TOPICS]
