#!/usr/bin/env python

from argparse import ArgumentParser
from ConfigParser import ConfigParser
import unicodecsv as csv
import xml.etree.ElementTree as ET
import os
import re
import sys
from time import sleep

from lookup import lookup_isbn

isbn_namespace = "{http://webservices.amazon.com/AWSECommerceService/2011-08-01}"
lccn_namespace = "{http://www.loc.gov/mods/v3}"

def validate_isbn(filename):
    good_infos = []
    current_case = None
    current_book_number = None
    with open(filename, 'rb') as f:
        data = csv.reader(f)
        for row in data:
            isbn = "isbn/{}.xml".format(row[1])
            if row[0] and not row[1]:
                current_case = row[0]
                current_book_number = 1
                continue
            if row[1]:
                good_info = []
                good_info.append(current_case)
                good_info.append(current_book_number)
                good_info.append('_{}'.format(row[1]))
                if os.path.exists(isbn): # and row[0].startswith('China'):
                    tree = ET.parse(isbn)
                    title = row[0]
                    for node in tree.findall('.//{0}ItemAttributes/{0}Title'.format(isbn_namespace)):
                        if re.sub('\W+', ' ', row[0]).lower() in re.sub('\W+', ' ', node.text).lower():
                            title = node.text
                            break
                    good_info.append(title)

                    current_book_number += 1
                    lowest_used = new_price = num_used = num_new = 0
                    url = None
                
                    for node in tree.findall('.//{0}OfferSummary/{0}LowestNewPrice/{0}Amount'.format(isbn_namespace)):
                        lowest_new = int(node.text)/100.0
                    for node in tree.findall('.//{0}OfferSummary/{0}LowestUsedPrice/{0}Amount'.format(isbn_namespace)):
                        lowest_used = int(node.text)/100.0
                    for node in tree.findall('.//{0}OfferSummary/{0}TotalNew'.format(isbn_namespace)):
                        num_new = node.text
                    for node in tree.findall('.//{0}OfferSummary/{0}TotalUsed'.format(isbn_namespace)):
                        num_used = node.text
                    for node in tree.findall('.//{0}Offers/{0}MoreOffersUrl'.format(isbn_namespace)):
                        url = node.text
                    for node in tree.findall('.//{0}ItemLinks/{0}ItemLink'.format(isbn_namespace)):
                        description = None
                        child_url = None
                        for child in node:
                            if child.tag.endswith('Description'):
                                description = child.text
                            elif child.tag.endswith('URL'):
                                child_url = child.text
                        if description == 'All Offers':
                            url = child_url

                    if not url:
                        print url
                    good_info.append(min(lowest_new, lowest_used))
                    good_info.append(max(lowest_new, lowest_used))
                    
                    good_info.append(lowest_new)
                    good_info.append(lowest_used)
                    good_info.append(num_new)
                    good_info.append(num_used)
                    good_info.append(url)
                else:
                    good_info.append('_{}'.format(row[1]))
                    good_info.append(row[0])
                    good_info += [0, 0, 0, 0, 0]
                good_infos.append(good_info)

    with open("price.csv", 'wb') as f:
        writer = csv.writer(f)
        writer.writerows(good_infos)

def validate_lccn(filename):
    with open(filename, 'rb') as f:
        data = csv.reader(f)
        for row in data:
            lccn = "lccn/{}.xml".format(row[1])
            good = False
            if row[1] and os.path.exists(lccn): # and row[0].startswith('China'):
                tree = ET.parse(lccn)
                for node in tree.findall('.//{0}titleInfo/{0}title'.format(lccn_namespace)):
                    if re.sub('\W+', ' ', row[0]).lower() in re.sub('\W+', ' ', node.text).lower():
                        good = True
            if good:
                for node in tree.findall('.//{0}identifier[@type=\'isbn\']'.format(lccn_namespace)):
                    print row[1], node.text, node.attrib['type']

def run(args):
    if args.service == 'isbn':
        validate_isbn(args.filename)
    elif args.service == 'lccn':
        validate_lccn(args.filename)

if __name__ == '__main__':
    parser = ArgumentParser(description="")
    parser.add_argument('filename', type=str, help="file to run this script against")
    parser.add_argument('service', type=str, help="service to hit")

    args = parser.parse_args()
    run(args)

