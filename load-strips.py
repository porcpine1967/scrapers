#!/usr/local/bin/python2.4
import datetime, urllib2, re, time
import sys
import strip

user_agent = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.12) Gecko/20101027 Ubuntu/10.04 (lucid) Firefox/3.6.12'

one_day = datetime.timedelta(1)
today = datetime.datetime.today()

def load_next_strips(name, url_builder, url_finder):
    last_strip = strip.get_last_strip(name)
    start = last_strip.day + one_day
    week_ctr = last_strip.week
    strips = []
    while start <= today:
        if start.weekday() == 0:
            week_ctr += 1
        url_to_call = url_builder(start)
        if url_to_call:
            try:
                request = urllib2.Request(url_to_call)
                request.add_header('User-Agent', user_agent)
                f = urllib2.urlopen(request)
                if url_to_call.endswith('jpg'):
                    url = url_to_call
                else:
                    url = url_finder(f)
                f.close()
                if url:
                    print 'Adding %s for %s' % (name, str(start))
                    s = strip.Strip(week_ctr, start, url, name)
                    s.save()
                    strips.append(s)
            except (urllib2.HTTPError, urllib2.URLError):
                print "Error opening %s" % (url_to_call)
            time.sleep(5)
        start = start + one_day

    return strips


def make_gocomics_url_builder(path, day_of_week=()):
    url_path = "http://www.gocomics.com/%s/%s/%02d/%02d"
    def gocomics_url_builder(date):
        if day_of_week and date.weekday() not in day_of_week:
            return ''
        return url_path % (path, date.year, date.month, date.day)
    return gocomics_url_builder

def gocomics_url_finder(f):
    url = ''
    for line in f:
        if 'assets.amuniversal.com' in line:
            m = re.search('content="(.*?)"', line)
            if m:
                url = m.group(1)
                break
    return url

def make_comics_url_builder(path, day_of_week=()):
    def comics_url_builder(date):
        if day_of_week and date.weekday() not in day_of_week:
            return ''
        url_path = 'http://comics.com/%s/%s-%s-%s/'
        return url_path % (path, date.year, date.month, date.day)
    return comics_url_builder

def comics_url_finder(f):
    url = ''
    for line in f:
        if '/str_strip/' in line:
            url = re.search('src="(http.*?)"', line).group(1)
            break
    return url
def big_nate_url_finder(f):
    url = ''
    for line in f:
        if 'class="strip"' in line:
            url = re.search('src="(http.*?)"', line).group(1)
            break
    return url

def pvp_url_builder(date):
    if date.weekday() == 6:
        return ''
    url_path = 'http://s3-us-west-2.amazonaws.com/pvponlinenew/img/comic/%s/0%s/pvp%s%02d%02d.jpg'
    return url_path % (date.year, date.month, date.year, date.month, date.day)

def pvp_url_finder(f):
    raise Exception('Should not be called')
    url = ''
    for line in f:
        if 'comic image' in line:
            m = re.search('src="(http.*?.png)"', line)
            if m:
                url = m.group(1)
                break
    return url

def foxtrot_url_builder(date):
    if date.weekday() != 6:
        return ''
    url_path = 'http://www.foxtrot.com/%s/%02d/%02d%02d%s/'
    return url_path % (date.year, date.month, date.month, date.day, date.year)

def foxtrot_url_finder(f):
    url = ''
    for line in f:
        if 'id="comics"' in line:
            m = re.search('src="(http.*?.png)"', line)
            if m:
                url = m.group(1)
                break
    return url


def dilbert_url_builder(date):
    url_path = 'http://www.dilbert.com/strip/%s-%02d-%02d/'
    return url_path % (date.year, date.month, date.day)

def dilbert_url_finder(f):
    url = ''
    for line in f:
        if "og:image" in line:
            m = re.search('content="([^"]+)"', line)
            if m:
                url = m.group(1)
                break
    return url
def penny_arcade_url_finder(f):
    url = ''
    for line in f:
        if "comicFrame" in line:
            m = re.search('src="(.*?\.jpg)"', line)
            if m:
                url = m.group(1)
                break
    return url

def penny_arcade_url_builder(date):
    if date.weekday() in (0, 2, 4):
        return 'http://penny-arcade.com/comic/%s/%02d/%02d/' % (date.year, date.month, date.day)
    return ''

if __name__ == '__main__':
    load_next_strips('Cul de Sac', make_gocomics_url_builder('culdesac'), gocomics_url_finder)
    load_next_strips('Dilbert', dilbert_url_builder, dilbert_url_finder)
    load_next_strips('Fox Trot', make_gocomics_url_builder('foxtrot', (6,)), gocomics_url_finder)
    # load_next_strips('Sylvia', make_gocomics_url_builder('sylvia', (0,1,2,3,4,5,)), gocomics_url_finder)
    load_next_strips('Tom the Dancing Bug', make_gocomics_url_builder('tomthedancingbug', (4,)), gocomics_url_finder)
    load_next_strips('Doonesbury', make_gocomics_url_builder('doonesbury'), gocomics_url_finder)
    # load_next_strips('Unstrange Phenomena', make_comics_url_builder('unstrange_phenomena', (0,1,2,3,4,)), comics_url_finder)
    load_next_strips('Big Nate', make_gocomics_url_builder('bignate'), gocomics_url_finder)
    # load_next_strips('PvP', pvp_url_builder, pvp_url_finder)
    # load_next_strips('Penny Arcade', penny_arcade_url_builder, penny_arcade_url_finder)

