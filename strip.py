#!/usr/local/bin/python
import datetime
import time
from subprocess import Popen, PIPE

class Strip(object):
    def __init__(self, week, day, url, name, page_url=''):
        self.week = week
        self.day = day
        self.url = url
        self.name = name
	self.page_url = page_url

    def insert_value(self):
        value="(%s,'%s','%s','%s','%s')"
        return value % (self.week, str(self.day), self.url, self.name, self.page_url)

    def save(self):
        sql = 'INSERT IGNORE INTO aliddet7_comics.culdesac (week, day, url, name, page_url) VALUES '
        sql += self.insert_value()
        result = execute_sql(sql)

def get_last_strip(name):
    sql = 'SELECT week, day, url, page_url FROM culdesac WHERE name = "%s" ORDER BY day DESC LIMIT 1' % name
    result = execute_sql(sql)
    row = result.split('\t')
    if len(row) > 1:
        week_string, day_string, url, page_url = row
        day = datetime.datetime(*(time.strptime(day_string, '%Y-%m-%d')[0:6]))
        week = int(week_string)
    else:
        week, day, url, page_url = (1, datetime.datetime.today() - datetime.timedelta(30), '', '')

    return Strip(week, day, url, name, page_url)

def execute_sql(sql):
    cmds = ['mysql',
            'aliddet7_comics',
            '-e', sql,
            '-BN',]
    p = Popen(cmds, stdout=PIPE)
    o = p.communicate()
    return o[0]

def run():
    s = get_last_strip('Doonesbury')
    print s.name
    print s.week
    print s.day
    print s.url    
if __name__ == '__main__':
    run()
