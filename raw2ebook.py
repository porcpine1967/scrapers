#!/usr/bin/env python
""" Analyzes text for paragraph breaks.
This script is for turning line/ocr text into html for later
conversion into an ebook.

Process:
Put text into duplicate files named "raw" and "clean"
> pdftotext x.pdf raw
Clean up obvious problems in clean:
* Remove line numbers, headers, and footers
* Look for odd characters and make sure they are supposed to be there
* Replace smart apostrophe's with dumb ones
** egrep -o "[^a-zA-Z0-9.,?;:()'\" -]" clean | sort -u
* Query replace all 1's with I's
* Check all numbers
* Check all isolated letters except a, A, and I
* Spell check file (with -l [lang] if not en-US)
** create file named custom.dict with header: personal_ws-1.1 en 1
** cat clean | aspell list | sort -u >> custom.dict
** Remove any words that might be misspelled
** aspell check clean --add-extra-dicts=./custom.dict
*** DO NOT FIX HYPHENATED WORDS. This will mess up determining para breaks

Save first ~300 lines to file named "test"
 Add paragraph tags to test
 test.py test

Add paragraph tags to new book.html
 test.py add -max (number from above)


Put this at the head of book.html. Update TITLE and AUTHOR
---
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<title>[TITLE]</title>
<style type="text/css">
p.author{text-indent:0;margin-top:1em;page-break-after:always;}
</style>
</head>
<body>
<h1>[TITLE]</h1>
<p class="author">by [AUTHOR]
---

Make all chapter headings <h2>...</h2>

Get first sentence of every paragraph
 test.py firsts

Start adding missed paragraph tags and removing wrongly-added tags
* turn off electric-indent-mode
* Review pdf for paragraph breaks
** On break, if exists in "firsts" file, move on
** On break, if not in "firsts" file, add new line with first few words to firsts file
** If line in firsts not a break, remove <p> tag from book.html and remove line from firsts
** If section break, add new line to firsts with nbsp
* Periodically run test.py check to make sure everything is in sync
* When bored run test.py update followed by test.py verify to move changes into book.html. Revove all executed lines from firsts

Fix up hyphenated words, add ellipses, re-run aspell, etc
"""

from argparse import ArgumentParser
from collections import Counter
import os

CAPITALS = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
)


class Line:
    """ Holds data about line."""

    def __init__(self, text):
        self.text = text
        self.last = False

    @property
    def length(self):
        """ Length of text."""
        return len(self.text)

    @property
    def ends_sentence(self):
        return self.text


def find_max_length():
    """ Determine max length of guessed new paragraph"""
    lengths = Counter()
    last_line = None
    with open("test") as f:
        for l in f:
            if "<p" in l:
                last_line = None
                continue
            if last_line:
                lengths[len(last_line)] += 1
            last_line = l.strip()
    for idx, k in enumerate(lengths):
        if idx > 5:
            break
        print(k, lengths[k])


def add_lines(max_length):
    """ Put guessed paragraph lines in file."""
    if os.path.exists("book.html"):
        answer = input("book.html exists. Overwrite? ")
        if not answer.lower().startswith("y"):
            return
    lines = [""]
    with open("clean") as f:
        for l in f:
            line = l.strip()
            if not line:
                continue
            if "<h2>" in line:
                lines.append(line)
            else:
                if len(lines[-1]) < max_length and line[0] in CAPITALS:
                    lines.append("<p>")
                lines.append(line)
    with open("book.html", "w") as f:
        for l in lines:
            f.write("{}\n".format(l))


def first_words(update):
    """ Writes out the first words of paragraphs."""
    is_first = False
    firsts = []
    with open("book.html") as f:
        for l in f:
            if is_first:
                if "<p" not in l and "<h2>" not in l:
                    firsts.append(l.strip())
            is_first = "<p" in l
    if update:
        with open("firsts", "w") as f:
            for first in firsts:
                writable = first if len(first) < 50 else first[:50]
                f.write("   {}\n".format(writable))
    return firsts


class First:
    """ Holder for line in firsts file."""

    def __init__(self, line):
        self.line = line

    @property
    def found(self):
        """ Whether already marked with paragraph"""
        return self.line.startswith("   ")

    def matches(self, line):
        """ Whether line in text matches the first."""
        if self.found:
            return line.startswith(self.line[3:])
        return line.startswith(self.line)


def checked_missed():
    """ Verify firsts file"""
    lines = []
    with open("book.html") as f:
        for l in f:
            lines.append(l.strip())
    firsts = []
    with open("firsts") as f:
        for l in f:
            firsts.append(First(l.rstrip()))
    first_index = 0
    new_lines = []
    for line in lines:
        if len(firsts) > first_index:
            if firsts[first_index].line == "nbsp":
                new_lines.append("nbsp")
                first_index += 1
            if firsts[first_index].matches(line):
                new_lines.append(firsts[first_index].line)
                first_index += 1
                print(new_lines[-1])
    print(len(firsts))
    print(len(new_lines))


def add_missed():
    """ Add paragraph tags to book.html"""
    lines = []
    with open("book.html") as f:
        for l in f:
            lines.append(l.strip())
    firsts = []
    with open("firsts") as f:
        for l in f:
            firsts.append(First(l.rstrip()))
    first_index = 0
    new_lines = []
    add_nbsp = False
    for line in lines:
        if add_nbsp and line == "<p>":
            new_lines.append("<p>&nbsp;")
            add_nbsp = False

        if len(firsts) > first_index:
            if firsts[first_index].line == "nbsp":
                add_nbsp = True
                first_index += 1
            if firsts[first_index].matches(line):
                if not firsts[first_index].found:
                    if add_nbsp:
                        new_lines.append("<p>&nbsp;")
                        add_nbsp = False
                    new_lines.append("<p>")
                first_index += 1
        new_lines.append(line)
    with open("book.html", "w") as f:
        for line in new_lines:
            f.write(line)
            f.write("\n")


def verify_updated():
    """ Makes sure all the lines are there"""
    firsts = []
    with open("firsts") as f:
        for l in f:
            firsts.append(l.strip())
    first_index = 0
    matching_counter = 0
    start_paras = first_words(False)
    for start_para in start_paras:
        if start_para.startswith(firsts[first_index]):
            matching_counter += 1
            if first_index + 1 < len(firsts):
                first_index += 1
                if firsts[first_index] == "nbsp":
                    matching_counter += 1
                    first_index += 1
    print(matching_counter)
    print(len(firsts))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("action")
    parser.add_argument("-max", type=int)
    args = parser.parse_args()
    if args.action == "check":
        checked_missed()
    elif args.action == "update":
        add_missed()
    elif args.action == "firsts":
        first_words(True)
    elif args.action == "verify":
        verify_updated()
    elif args.action == "test":
        find_max_length()
    elif args.action == "add":
        add_lines(args.max)
    else:
        print("WRONG")
