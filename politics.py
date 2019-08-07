#!/usr/bin/env python

from datetime import datetime
import re
from subprocess import Popen, PIPE
import urllib2


POLITICS_RSS = 'http://rss.acast.com/talkingpolitics'
PUBDATE = re.compile('<pubDate>(.*)</pubDate>')
ENCLOSURE = re.compile('<enclosure url="([^"]+mp3)')
PUBDATE_PATTERN = '%a, %d %b %Y %H:%M:%S %Z'
PUBDATE_PATTERN_Z = '%Y-%m-%dT%H:%M:%S.000Z'

def get_politics_podcasts():
    current_date = None
    printed_count = 0
    req = urllib2.Request(POLITICS_RSS)
    req.add_header('User-agent', 'Mozilla 5.10')
    response = urllib2.urlopen(req)

    for l in response:
        pd = PUBDATE.search(l)

        if pd:
            if pd.group(1).endswith('Z'):
                current_date = datetime.strptime(pd.group(1), PUBDATE_PATTERN_Z)
            else:
                current_date = datetime.strptime(pd.group(1), PUBDATE_PATTERN)

        e = ENCLOSURE.search(l)
        if printed_count < 7 and e:
            print current_date, e.group(1)
            printed_count += 1

    

if __name__ == '__main__':
    get_politics_podcasts()
