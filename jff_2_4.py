#!/usr/bin/env python

from datetime import datetime
import re
from subprocess import Popen, PIPE
import urllib2

URL_TEMPLATE= re.compile(r'http:.*?mp3')
PODCAST_RSS = 'http://savoirs.rfi.fr/fr/apprendre-enseigner/langue-francaise/journal-en-francais-facile'

class Podcast(object):
    def __init__(self, url):
        self.url = url.replace('\\', '')
        try:
            self.date = datetime(int(self.url[-12:-8]), int(self.url[-8:-6]), int(self.url[-6:-4]))
            self.mysql_date = self.date.strftime('%Y-%m-%d')
        except:
            self.mysql_date = None           

    def save(self):
        count_sql = "select count(*) from jff where day = '%s'" % self.mysql_date
        if execute_sql(count_sql).strip() == str(0):
            insert_sql = "INSERT INTO jff VALUES('%s', '%s')" % (self.mysql_date, self.url,)
            execute_sql(insert_sql)

def text_value(parent, child_tag):
    """ Returns text value of first child tag of parent."""
    for n in parent.getElementsByTagName(child_tag):
        return n.firstChild.nodeValue

def execute_sql(sql):
    cmds = ['mysql',
            'aliddet7_comics',
            '-e', sql,
            '-BN',]
    p = Popen(cmds, stdout=PIPE)
    o = p.communicate()
    return o[0]

def get_podcasts_from_file():
    lines = []
    with open('/home/jdettmann/Desktop/jff.html', 'rb') as f:
        for l in f:
            lines.append(l.strip())
    return get_podcasts(lines)

def get_podcasts_from_website():
    response = urllib2.urlopen(PODCAST_RSS)
    return get_podcasts(response)

def get_podcasts(file_thing):
    podcasts = []
    for l in file_thing:
        for url in re.findall(URL_TEMPLATE, l):
            podcast = Podcast(url)
            if podcast.mysql_date:
                podcasts.append(podcast)
    returnable = []
    
    for idx, podcast in enumerate(sorted(podcasts, reverse=True, key=lambda x: x.date)):
        returnable.append(podcast)
    return returnable
    

if __name__ == '__main__':
    # podcasts = get_podcasts_from_file()
    podcasts = get_podcasts_from_website()
    for podcast in podcasts:
        print podcast.date, podcast.url
        podcast.save()

