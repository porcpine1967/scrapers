import datetime
from subprocess import Popen, PIPE
import time
import urllib.request
import xml.etree.ElementTree as ET

import boto3

from selenium import webdriver
from selenium.webdriver.common.by import By

awsuser = 'cliuser'

bucket_name = 'tourneyopportunities.net'
file_name = 'comics.rss'

TEMPLATE = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Comics</title><description>Comics from various sites on the internets</description><link>https://tourneyopportunities.net/comics.rss</link><lastBuildDate>{today}</lastBuildDate><pubDate>{today}</pubDate>
{items}
</channel></rss>
"""

user_agent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.12) Gecko/20101027 Ubuntu/10.04 (lucid) Firefox/3.6.12"

rss_date_format = '%a, %d %b %Y %H:%M:00 +0000'
XPATH= '//meta[starts-with(@content,"https://featureassets.gocomics.com/assets")]'

def call_os(cmds):
    p = Popen(cmds, stdout=PIPE, stderr=PIPE)
    return p.communicate()

def check_aws_logged_in():
    cmds = ('aws', 'sts', 'get-caller-identity', '--profile', awsuser,)
    good, bad = call_os(cmds)
    if bad:
        cmds = ('aws', 'sso', 'login', '--profile', awsuser,)
        good, bad = call_os(cmds)
    if not good:
        print(f"Could not log in to aws: {bad}")
        sys.exit(1)

class Strip:
    url_path = "https://www.gocomics.com/{}/{}/{:02}/{:02}"
    def item(self, browser, date):
        if date.weekday() in self.days:
             url_to_call = Strip.url_path.format(self.path, date.year, date.month, date.day)
             print(f'calling {url_to_call}')
             browser.get(url_to_call)
             meta_line = browser.find_element(By.XPATH, XPATH)
             url = meta_line.get_attribute('content')
             if url:
                 print(f'asset_url {url}')
                 time.sleep(2)
                 i = Item()
                 i.title = self.name
                 i.src = url
                 i.pub_date = date
                 return i

    def new_or_existing(self, browser, date, existing):
        existing_item = self.item_exists(date, existing)
        if existing_item:
            return existing_item
        if date > datetime.date.today() - datetime.timedelta(20):
            return self.item(browser, date)

    def item_exists(self, date, existing):
        if date.weekday() in self.days:
            for item in existing:
                if item.title == self.name and item.pub_date == date:
                    return item

class Sylvia(Strip):
    def __init__(self):
        self.days = (0, 1, 2, 3, 4, 5,)
        self.name = 'Sylvia'
        self.path = 'sylvia'


class CalvinAndHobbes(Strip):
    def __init__(self):
        self.days = (0, 1, 2, 3, 4, 5, 6)
        self.name = 'Calvin and Hobbes'
        self.path = 'calvinandhobbes'

class Peanuts(Strip):
    def __init__(self):
        self.days = (0, 1, 2, 3, 4, 5, 6)
        self.name = 'Peanuts'
        self.path = 'peanuts'

class Boondocks(Strip):
    def __init__(self):
        self.days = (0, 1, 2, 3, 4, 5, 6)
        self.name = 'Boondocks'
        self.path = 'boondocks'

class Doonesbury(Strip):
    def __init__(self):
        self.days = (0, 1, 2, 3, 4, 5, 6)
        self.name = 'Doonesbury'
        self.path = 'doonesbury'

class FoxTrot(Strip):
    def __init__(self):
        self.days = (6,)
        self.name = 'Fox Trot'
        self.path = 'foxtrot'

class TomTheDancingBug(Strip):
    def __init__(self):
        self.days = (4,)
        self.name = 'Tom the Dancing Bug'
        self.path = 'tomthedancingbug'

class Item:
    def __init__(self):
        self.title = ''
        self.src = ''
        self.pub_date = ''

    @property
    def guid(self):
        return self.src

    @property
    def formatted_pub_date(self):
        return self.pub_date.strftime(rss_date_format)


    @property
    def rss(self):
        return f"""<item>
  <title>{self.title}</title>
  <description>
    <![CDATA[<img alt="{self.title}" src="{self.src}" />]]>
  </description>
  <link>{self.src}</link>
  <guid>{self.guid}</guid>
  <pubDate>{self.formatted_pub_date}</pubDate>
</item>"""

def item_from_xml(item):
    i = Item()
    i.title = item.find('./title').text
    i.src = item.find('./link').text
    pub_date = item.find('./pubDate').text
    i.pub_date = datetime.datetime.strptime(pub_date, rss_date_format).date()
    return i

def existing_items(client):
    items = []
    obj = client.get_object(Bucket=bucket_name, Key=file_name)
    tree = ET.parse(obj['Body'])
    root = tree.getroot()
    for item_node in root.iter('item'):
        item = item_from_xml(item_node)
        items.append(item)
    return items

def month_of_items(client, browser):
    existing = existing_items(client)
    items = []
    for c in (Sylvia, Doonesbury, TomTheDancingBug, FoxTrot, Peanuts, CalvinAndHobbes, Boondocks):
        obj = c()
        print(f'Handling {obj.name}')
        for i in range(28):
            date = datetime.date.today() - datetime.timedelta(i)
            item = obj.new_or_existing(browser, date, existing)
            if item:
                items.append(item)
    return items

def rss(items):
    items_s = '\n'.join([item.rss for item in items])
    return TEMPLATE.format(today=datetime.datetime.today().strftime(rss_date_format), items=items_s)

def lambda_handler(event, context):
    browser = webdriver.Chrome()
    try:
        check_aws_logged_in()
        session = boto3.Session(profile_name='cliuser')
        s3 = session.client('s3', 'us-east-1')
        items = month_of_items(s3, browser)
        resp = s3.put_object(Bucket=bucket_name, Key=file_name, Body=rss(items))
        print(resp)
    finally:
        browser.close()

if __name__ == '__main__':
    lambda_handler(None, None)
