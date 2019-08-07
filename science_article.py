#!/usr/local/bin/python
import datetime
import time
import HTMLParser
import os
import re
from subprocess import Popen, PIPE
import urllib2

RSS_URL = 'http://science.sciencemag.org/rss/current.xml'
LINK_PATTERN = re.compile(r'<item rdf:about="(.*)"')

def full_url(short_url):
    path = short_url.split('?')[0]
    bits = path.split('/')
    if '-' in bits[-1]:
        pdfbits = bits[-1].split('-')
        return 'http://science.sciencemag.org/content/%s/%s/%s.%s.full' % (bits[-3], bits[-2], pdfbits[0], ord(pdfbits[1]) - 96)
    else:
        return 'http://science.sciencemag.org/content/%s/%s/%s.full' % (bits[-3], bits[-2], bits[-1])

class Article(object):
    def __init__(self, article_parser):
        self.title = article_parser.title.replace("'", '')
        self.description = article_parser.description.replace("'", '')
        self.url = article_parser.link
        self.day = article_parser.day
        if article_parser.readability:
            self.readability = article_parser.readability.replace("'", '')
        else:
            self.readability = ''

    def insert_value(self):
        value=u"('%s','%s','%s','%s','%s')"
        return value % (self.title, str(self.day), self.url, self.description, self.readability)

    def save(self):
        sql = u'INSERT INTO aliddet7_comics.science (title, day, url, description, readability) VALUES '
        sql += self.insert_value()
        return execute_sql(sql)

def execute_sql(sql):
    cmds = ['mysql',
            'aliddet7_comics',
            '-e', sql,
            '-BN',]
    p = Popen(cmds, stdout=PIPE, stderr=PIPE)
    o = p.communicate()
    return o

class ArticleParser(HTMLParser.HTMLParser):
    def __init__(self, html_file):
        HTMLParser.HTMLParser.__init__(self)
        self.file_as_string = u""
        for l in html_file:
            self.file_as_string += l.decode('utf_8')
        self.current_tag = None
        self.title = None
        self.description = None
        self.readability = None
        self.day = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            for k, v in attrs:
                if k == 'class' and v == 'pane-title':
                    self.current_tag = 'readability'
        if tag == 'meta':
            is_title = False
            is_desc = False
            is_date = False
            content = None
            for k, v in attrs:
                if k == 'name' and v == 'DC.Date':
                    is_date = True
                elif k == 'name' and v == 'DC.Description':
                    is_desc = True
                elif k == 'name' and v == 'DC.Title':
                    is_title = True
                if k == 'content':
                    content = v
            if is_date:
                self.day = content
            if is_desc:
                d = []
                for idx, line in enumerate(content.split('\n')):
                    if idx == 0 and '</img>' in line:
                        continue
                    if line.startswith('1.') or line.strip().startswith('[1]'):
                        break
                    if line.strip():
                        d.append('<p>' + line.strip() + '</p>')
                self.description = '\n'.join(d)
            if is_title:
                self.title = content
    def handle_endtag(self, tag):
        self.current_tag = None
    def handle_data(self, data):
        if self.current_tag == 'readability' and not self.readability:
            if data == 'More options':
                self.readability = 'PDF'
            elif data == 'Log in to view full text':
                self.readability = 'Log in'
            else:
                self.readability = data

def download_articles_for_local(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    links = set()
    for l in urllib2.urlopen(RSS_URL):
        m = LINK_PATTERN.search(l)
        if m:
            links.add(m.group(1))
    for idx, short_link in enumerate(links):
        link = full_url(short_link)
        print link
        response = urllib2.urlopen(link)
        with open('%s/artice_%s.html' % (dirname, idx), 'w') as f:
            for l in response:
                f.write(l)

def test_local_articles(dirname):
    if not os.path.exists(dirname) or len(os.listdir(dirname)) < 1:
        print 'downloading articles...'
        download_articles_for_local(dirname)
    for f in os.listdir(dirname):
        test_local_article('%s/%s' % (dirname, f))

def test_local_article(fname):
    print 'testing', fname
    a = ArticleParser(open(fname))
    a.feed(a.file_as_string)

def get_article(short_link):
    link = full_url(short_link)
    response = urllib2.urlopen(link)
    a = ArticleParser(response)
    a.feed(a.file_as_string)
    a.link = link
    return Article(a)

def get_links():
    links = set()
    for l in urllib2.urlopen(RSS_URL):
        m = LINK_PATTERN.search(l)
        if m:
            links.add(m.group(1))
    return links

def article_exists(link):
    result = execute_sql('select count(*) from science where url = "%s"' % full_url(link))
    return int(result[0])

def run():
    links = get_links()
    save_ctr = 0
    for link in links:
        if not article_exists(link):
            _, err = get_article(link).save()
            if not err:
                save_ctr += 1
            if save_ctr > len(links)/7:
                break
    print save_ctr, 'articles'

if __name__ == '__main__':
    run()
