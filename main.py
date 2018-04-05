from googleapiclient.discovery import build
from os import system

def kill_drivers(drivers):
    for driver in drivers:
        driver.quit()

def naive_approach(question, answers):
    DRIVERS[0].get('https://www.google.com/search?q=' + question)
    for i in range(len(answers)):
        DRIVERS[i + 1].get('https://www.google.com/search?q=' + question + ' "' + answers[i] + '"')

def google_search(query, start):
    service = build("customsearch", "v1", developerKey=CREDENTIALS.api_key)
    res = service.cse().list(q=query, cx=CREDENTIALS.cse_id, start=start).execute()
    return res

def metric1Func(question, answers):
    met1 = [0, 0, 0]
    res = google_search(question, None)
    items = str(res['items']).lower()
    met1[0] = items.count(answers[0].lower())
    met1[1] = items.count(answers[1].lower())
    met1[2] = items.count(answers[2].lower()) 
    return met1

def metric2Func(question, answers):
    met2 = [0, 0, 0]
    res0 = google_search(question + ' "' + answers[0] + '"', None)
    res1 = google_search(question + ' "' + answers[1] + '"', None)
    res2 = google_search(question + ' "' + answers[2] + '"', None)
    return [int(res0['searchInformation']['totalResults']), int(res1['searchInformation']['totalResults']), int(res2['searchInformation']['totalResults'])]

def predict(metric1, metric2, answers):
    max1 = metric1[0]
    max2 = metric2[0]
    for x in range(1, 3):
        if metric1[x] > max1:
            max1 = metric1[x]
        if metric2[x] > max2:
            max2 = metric2[x]
    if metric1.count(0) == 3:
        return answers[metric2.index(max2)]
    elif metric1.count(max1) == 1:
        if metric1.index(max1) == metric2.index(max2):
            return answers[metric1.index(max1)]
        else:
            percent1 = max1 / sum(metric1)
            percent2 = max2 / sum(metric2)
            if percent1 >= percent2:
                return answers[metric1.index(max1)]
            else:
                return answers[metric2.index(max2)]
    elif metric1.count(max1) == 3:
        return answers[metric2.index(max2)]
    else:
        return answers[metric2.index(max2)]

def q_analysis(question, answers):
    question = question.replace('"', '')
    x = predict(metric1Func(question, answers), metric2Func(question, answers), answers)
    print x
    system('osascript -e \'display notification "' + x + '" with title "' + question + '"\'')
    naive_approach(question, answers)

globals()['N_QUESTIONS'] = 3


from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)
HOUR = timedelta(hours=1)

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

globals()['utc'] = UTC()

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

globals()['LOCAL'] = LocalTimezone()


from ast import literal_eval

def on_open(ws):
    print 'connected'

def on_message(ws, message):
    try:
        message = literal_eval(message)
        type = message['type']
        if type == 'question':
            print message['question']
            for answer in message['answers']:
                print '-', answer['text']
            q_analysis(message['question'].decode('ascii', 'replace').encode('ascii'), [answer['text'].decode('ascii', 'replace').encode('ascii') for answer in message['answers']])
        #if type == 'interaction':
            #metadata = message['metadata']
            #print metadata['username'] + ': ' + metadata['message']
    except Exception as e:
        print e

def on_error(ws, error):
    print '\n' + error + '\n'

def on_close(ws):
    print 'disconnected'

def hack(trivia_hq, google_cse):
    from requests import get
    from dateutil.parser import parse
    from selenium import webdriver
    from atexit import register
    from websocket import WebSocketApp
    
    headers = {
        'User-Agent': 'hq-viewer/1.2.4 (iPhone; iOS 11.1.1; Scale/3.00)',
        'Authorization': 'Bearer ' + trivia_hq.bearer_token,
        'x-hq-client': 'iOS/1.2.4 b59'
    }
    
    try:
        response = get('https://api-quiz.hype.space/shows/now?type=hq&userId=' + trivia_hq.user_id, headers).json()
    except Exception as e:
        quit('Server error fetching show schedule: ' + repr(e))

    nextShowTime = parse(response['nextShowTime']) if response['nextShowTime'] else datetime.now(utc)
    nextShowPrize = response['nextShowPrize']

    broadcast = response['broadcast']
    if broadcast:
        streamUrl = broadcast['streamUrl']
        socketUrl = broadcast['socketUrl'].replace('https', 'wss', 1)
    else:
        quit('Broadcast ended. Next show at ' + str(nextShowTime.astimezone(LOCAL)) + ' for ' + nextShowPrize + '.')

    #system('/Applications/VLC.app/Contents/MacOS/VLC ' + streamUrl + ' &')
    
    n_drivers = N_QUESTIONS + 1
    globals()['DRIVERS'] = [webdriver.Chrome() for _ in range(n_drivers)]
    register(kill_drivers, DRIVERS)
    
    triviaClient = WebSocketApp(
        socketUrl,
        on_open = on_open,
        on_message = on_message,
        on_error = on_error,
        on_close = on_close,
        header = headers
    )

    globals()['CREDENTIALS'] = google_cse
    
    while True:
        triviaClient.run_forever()

if __name__ == '__main__':
    from credentials import trivia_hq, google_cse
    hack(trivia_hq, google_cse)
