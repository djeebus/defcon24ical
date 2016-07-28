import datetime
import icalendar
import os
import re
import requests
import time
import pytz

from lxml import etree

vegas = pytz.timezone('US/Pacific')
DEFCON_NUMBER = 24
day_one = datetime.date(2016, 8, 4)

day = datetime.timedelta(days=1)
dates = {
    'Thursday': day_one + (day * 0),
    'Friday':   day_one + (day * 1),
    'Saturday': day_one + (day * 2),
    'Sunday':   day_one + (day * 3),
}

expected_counts = {
    'Thursday': 32,
    'Friday': 44,
    'Saturday': 48,
    'Sunday': 28,
}


title_clean_up = {
    'vlanhoppingarppoisoningmitmattacksinvirtualizedenvironments': 'vlanhoppingarppoisoningandmaninthemiddleattacksinvirtualizedenvironments',
    'toxicproxiesbypassinghttpsvpnstopwnyouronlineidentity': 'toxicproxiesbypassinghttpsandvpnstopwnyouronlineidentity',
    'amonitordarklyreversingandexploitingubiquitousonscreendisplaycontrollersinmodernmonitors': 'amonitordarklyreversingandexploitingubiquitous',
    'npreeavesdroppingonthemachines': 'eavesdroppingonthemachines',
    'breakingtheinternetofvibratingthingswhatwelearnedreverseengineeringbluetoothandinternetenabledadulttoys': 'breakingtheinternetofvibratingthings',
    'hackinghotelkeysandpointofsalesystemsattackingsystemsusingmagneticsecuretransmission': 'hackinghotelkeysandpointofsalesystems',
    'howtogetgoodseatsinthesecuritytheaterhackingboardingpassesforfunandprofit': 'howtogetgoodseatsinthesecuritytheaterhackingboardingpassesforfunprofit',
    '101sentientstoragedossdshaveamindoftheirown': 'sentientstoragedossdshaveamindoftheirown',
    'canyoutrustautonomousvehiclescontactlessattacksagainstsensorsofselfdrivingvehicle': 'canyoutrustautonomousvehiclescontactlessattacks',
    'droneshijackingmultidimensionalattackvectorsandcountermeasures': 'droneshijackingmultidimensionalattackvectorscountermeasures',
    'honeyonionsexposingsnoopingtorhsdirrelays': 'honeyonionsexposingsnoopingtorhsdirrelaysguevaranoubiramiralisanatinia',
    'hidingwookieesinhttphttpsmugglingisathingweshouldknowbetterandcareabout': 'hidingwookieesinhttphttpsmuggling',
    'sixdegreesofdomainadminusinggraphtheorytoaccelerateredteamoperations': 'sixdegreesofdomainadmin',
    'propagandaandyouandyourdeviceshowmediadevicescanbeusedtocoerceandhowthesamedevicescanbeusedtofightback': 'propagandaandyouandyourdevices',
    'forcingatargetedltecellphoneintoanunsafenetwork': 'forcingatargetedltecellphoneintounsafenetwork',
    'maelstromareyouplayingwithafulldeckusinganewlydevelopedattacklifecyclegametoeducatedemonstrateandevangelize': 'maelstromareyouplayingwithafulldeck',
    'playingthroughthepaintheimpactofsecretsanddarkknowledgeonsecurityandintelligenceprofessionals': 'playingthroughthepaintheimpactofsecretsanddarkknowledge',
    'howtoremmotecontrolanairlinersecurityflawsinavionics': 'howtoremotecontrolanairlinersecurityflawsinavionics',
}

if os.name == 'nt':
    import win_unicode_console
    win_unicode_console.enable()

here = os.path.dirname(os.path.abspath(__file__))

DEFCON_ROOT_PATH = 'https://www.defcon.org/html/defcon-{num}'.format(num=DEFCON_NUMBER)


def url(url_fmt):
    return url_fmt.format(root=DEFCON_ROOT_PATH, num=DEFCON_NUMBER)


DEFCON_SCHEDULE_PATH = os.path.join(here, 'schedule.html')
DEFCON_SCHEDULE_URL = url('{root}/dc-{num}-schedule.html')
DEFCON_SPEAKERS_PATH = os.path.join(here, 'speakers.html')
DEFCON_SPEAKERS_URL = url('{root}/dc-{num}-speakers.html')
DEFCON_ICAL_PATH = os.path.join(here, 'defcon%s.ics' % DEFCON_NUMBER)


def get_url(url, path):
    if not os.path.isfile(path):
        response = requests.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if not chunk:  # keep-alive
                    continue

                f.write(chunk)
            f.flush()

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    return ' '.join(lines)


def mkdate(day, tm):
    return datetime.datetime.combine(dates[day], tm)


chars = re.compile(r'[^a-z^0-9]', re.IGNORECASE)


def clean_title(title):
    text = chars.sub('', title.lower())
    text = title_clean_up.get(text, text)
    return text


schedule_content = get_url(DEFCON_SCHEDULE_URL,
                           DEFCON_SCHEDULE_PATH)

speakers_content = get_url(DEFCON_SPEAKERS_URL,
                           DEFCON_SPEAKERS_PATH)


parser = etree.HTMLParser(encoding='utf-8')
tree = etree.fromstring(schedule_content, parser)

presentations_by_day_track = {}
presentations_by_title = {}
for day in tree.xpath('//h2[@class="title"]'):
    day_name = day.text
    presentations_by_day_track.setdefault(day_name, {})

    siblings = list(day.itersiblings())
    indices = []
    for index, s in enumerate(siblings):
        if s.tag == 'li':
            indices.append(index)
    for index in indices:
        siblings[index:index] = list(siblings[index].iterchildren())

    count = 0
    for p_time in siblings:
        if p_time.tag == 'h2':
            break

        if p_time.tag != 'h3':
            continue

        time_text = p_time.text

        track_wrapper = p_time.getnext()  # should be the ul
        for li in track_wrapper.getchildren():
            try:
                track = next(li.iterchildren('h4'))
            except StopIteration:
                continue

            track_text = track.text
            track_schedule = presentations_by_day_track[day_name].setdefault(track.text, [])

            track_info = list(track.itersiblings('p'))
            if li.get('class') == 'emptyRoom' and not track_info:
                track_schedule.append(None)
                count += 1
                continue

            title = track_info[0]

            try:
                title = next(title.iterchildren('a'))
            except StopIteration:
                pass

            title_text = title.text
            title_clean = clean_title(title_text)
            if presentations_by_title.get(title_clean):
                count += 1
                continue

            title_href = title.get('href')

            if len(track_info) > 1:
                speaker = track_info[1].text
            else:
                # track has no speaker
                speaker = None

            # print("\t\tTRACK: %s" % track.text)
            # print("\t\t\t%s: %s" % (title_text, speaker.text))
            # print(speaker.text)

            start = time.strptime(time_text, '%H:%M')
            start = datetime.time(start.tm_hour, start.tm_min, tzinfo=vegas)
            start = mkdate(day_name, start)

            presentation = {
                'key': title_clean,
                'start': start,
                'title': title_text,
                'speaker': speaker,
            }

            track_schedule.append(presentation)
            presentations_by_title[title_clean] = presentation
            count += 1

    expected = expected_counts[day_name]
    if expected != count:
        print("expected %s classes on %s, found %s" % (expected, day_name, count))
        exit(1)


print("found %s presentations" % len(presentations_by_title))

parser = etree.HTMLParser(encoding='utf-8')
tree = etree.fromstring(speakers_content, parser)

article_count = 0
for article in list(tree.xpath('//article')):
    try:
        title = next(article.iterchildren('h2'))
    except StopIteration:
        continue

    title_text = title.text
    if not title_text:
        continue

    presentation_key = clean_title(title_text)
    presentation = presentations_by_title.get(presentation_key)
    if not presentation:
        continue

    article_count += 1
    print("+++ %s" % presentation_key)
    article_text = ''.join(article.itertext())
    if not article_text:
        print(" --- %s" % presentation_key)

    presentation['details'] = article_text


# expected_article_counts = len(presentations_by_title)
# if article_count != expected_article_counts:
#     print("only found %s articles, expected %s"
#           % (article_count, expected_article_counts))
#     exit(1)


calendar = icalendar.Calendar()
calendar.add('prodid', '-//DefCon %s Schedule//defcon.org//' % DEFCON_NUMBER)
calendar.add('version', '2.0')

for day, tracks in presentations_by_day_track.items():
    for track, sched in tracks.items():
        for index, presentation in enumerate(sched):
            if presentation is None:
                continue

            next_presentation = sched[index + 1] if len(sched) >= index + 2 else None
            if next_presentation and next_presentation['title'] == presentation['title']:
                continue

            prev_presentation = sched[index - 1] if index > 0 else None

            event = icalendar.Event()
            event['location'] = icalendar.vText(track)
            event.add('summary', presentation['title'])
            details = presentation.get('details')
            if details:
                event.add('DESCRIPTION', presentation['details'])
            else:
                print("missing desc: %s" % presentation['key'])

            if prev_presentation and prev_presentation['title'] == presentation['title']:
                start = prev_presentation['start']
            else:
                start = presentation['start']
            event.add('dtstart', start)

            if next_presentation is not None:
                end = next_presentation['start']
                event.add('dtend', end)

            if 'dtend' not in event:
                event.add('dtend', start + datetime.timedelta(hours=1))

            calendar.add_component(event)

with open(DEFCON_ICAL_PATH, 'wb') as f:
    f.write(calendar.to_ical())
    f.flush()
