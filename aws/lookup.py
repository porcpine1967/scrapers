#!/usr/bin/env python

from datetime import datetime
from hashlib import sha256
import hmac
import urllib
import urllib2

ACCESS = ''
KEY = ''

ENDPOINT = "webservices.amazon.com"
TAG = ''
PATH = "/onca/xml";

"""
http://webservices.amazon.com/onca/xml?
Service=AWSECommerceService
&Operation=ItemLookup
&ResponseGroup=Large
&SearchIndex=All
&IdType=ISBN
&ItemId=076243631X
&AWSAccessKeyId=[Your_AWSAccessKeyID]
&AssociateTag=[Your_AssociateTag]
&Timestamp=[YYYY-MM-DDThh:mm:ssZ]
&Signature=[Request_Signature]
"""

def lookup_lccn(lccn):
    mod_lccn = "{}{:06d}".format(lccn[0:2], int(lccn[2:]))
    url = "http://lccn.loc.gov/{}/mods".format(mod_lccn)
    f = urllib2.urlopen(url)
    return f.read()

def isbn_signature(isbn, timestamp):
    to_sign = "GET\n"
    to_sign += ENDPOINT
    to_sign += "\n"
    to_sign += PATH
    to_sign += "\n"

    to_sign += "AWSAccessKeyId={}&".format(ACCESS)
    to_sign += "AssociateTag={}&".format(TAG)
    to_sign += 'IdType=ISBN&'
    to_sign += "ItemId={}&".format(isbn)
    to_sign += 'Operation=ItemLookup&'
    to_sign += 'ResponseGroup=Large&'
    to_sign += 'SearchIndex=All&'
    to_sign += 'Service=AWSECommerceService&'
    to_sign += "Timestamp={}".format(timestamp.replace(':', '%3A'))
    m = hmac.new(KEY, to_sign, sha256)
    
    return m.digest().encode("base64").rstrip('\n')

def lookup_isbn(isbn):
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    data = {
        'AWSAccessKeyId': ACCESS,
        'AssociateTag': TAG,
        'IdType': 'ISBN',
        'ItemId': isbn,
        'Operation': 'ItemLookup',
        'ResponseGroup': 'Large',
        'SearchIndex': 'All',
        'Service': 'AWSECommerceService',
        'Timestamp': timestamp,
        'Signature': isbn_signature(isbn, timestamp),
        }
    url = "http://{}{}?{}".format(ENDPOINT, PATH, urllib.urlencode(data))
    f = urllib2.urlopen(url)
    return f.read()

def power_signature(query, timestamp):
    to_sign = "GET\n"
    to_sign += ENDPOINT
    to_sign += "\n"
    to_sign += PATH
    to_sign += "\n"

    to_sign += "AWSAccessKeyId={}&".format(ACCESS)
    to_sign += "AssociateTag={}&".format(TAG)
    to_sign += 'Operation=ItemSearch&'
    to_sign += "Power={}&".format(urllib.quote(query))
    to_sign += 'ResponseGroup=Large&'
    to_sign += 'SearchIndex=Books&'
    to_sign += 'Service=AWSECommerceService&'
    to_sign += "Timestamp={}".format(urllib.quote(timestamp))
    m = hmac.new(KEY, to_sign, sha256)
    
    return m.digest().encode("base64").rstrip('\n')
    
def power_lookup(info):
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    """
    http://webservices.amazon.com/onca/xml?
    AWSAccessKeyId=[Access Key ID]&
    AssociateTag=[Associate Tag]&
    Operation=ItemSearch&
    Power=subject:history%20and%20(spain%20or%20mexico)%20and%20not%20military%20and%20language:spanish&
        SearchIndex=Books&
    Service=AWSECommerceService&
    Timestamp=[YYYY-MM-DDThh:mm:ssZ]&
    Signature=[Request Signature]
    """
    search = []
    for k, v in info.items():
        search.append('{}:"{}"'.format(k, v.encode('utf8')))
    query = ' and '.join(search)
    data = {
        'AWSAccessKeyId': ACCESS,
        'AssociateTag': TAG,
        'Operation': 'ItemSearch',
        'Power': query,
        'ResponseGroup': 'Large',
        'SearchIndex': 'Books',
        'Service': 'AWSECommerceService',
        'Timestamp': timestamp,
        'Signature': power_signature(query, timestamp),
        }
    query_string = '&'.join(["{}={}".format(k, v) for k, v in data.items()])
    query_string = urllib.urlencode(data)
    url = "http://{}{}?{}".format(ENDPOINT, PATH, query_string)
    f = urllib2.urlopen(url)
    return f.read()
                      
def test_power_lookup():
    info = {
        'author': 'Petroski, Henry.',
        'title': 'To engineer is human',
        }
    with open('test.xml', 'wb') as f:
        f.write(power_lookup(info))
    print power_lookup(info)
if __name__ == '__main__':
    # print lookup_lccn('588622')
    print test_power_lookup()
