#!/usr/bin/env python
"""
This program takes xml generated from a text-based pdf
and turns it into html for generation into an ebook by Calibre

Step 1:
Convert the pdf to xml with the command-line tool pdftohtml

pdftohtml -xml [path to pdf] [path to exported xml file]

Step 2:
Analyse the pdf

This is the default behavior of the program

xml_pdf [path to xml file]

Output Example:
diff:   21  count: 11585
diff:   20  count: 5220
diff:   41  count:  149
diff:   42  count:   90
diff:   86  count:   23
diff:   62  count:   19
diff:   48  count:   12
diff:   45  count:    9
diff:   65  count:    5
diff:   69  count:    5
left:    7  count: 2610
left:   50  count: 1883
left:   51  count: 1825
left:   41  count: 1614
left:   16  count: 1527
left:    9  count: 1455
left:   52  count: 1150
left:   18  count: 1134
left:    8  count: 1127
left:   14  count:  857
font class_0:   24313
font class_3:     317
font class_2:      65
font class_1:      44
font class_4:       1

How to read the output
diff: how many xml units are between one line and the next
count: how many times that line diff shows up
The diff is useful for the 'buf' parameter to tell when lines that are a little offset should be on the same logical line.

These two are useful for determining 'para_break' if paragraphs are indicated by space between lines.

left: number of times a left margin of this turns up. Useful for determining 'para_break' if paragraphs are indented

font: number of lines that use this font class. Useful for determining default font.

Step 3:
Update the xml with config values


From the analysis, determine the values for the following
configuration items:
top_margin: If the pages have headers, chop them off by putting
them above this line
bottom_margin: If the pages have footers, chop them off by putting
them below this line
para_break: If paragraphs are indicated by space, this is the amount of
difference between the tops of consecutive lines that imply a new
paragraph should start.
If paragraphs are indicated by indentation, this is the breakoff
point after which the beginning of a line indicates a new paragraph
buf: For Composite Lines (when a logical line of text is broken into
separate xml nodes for formatting reasons), the 'top' of the line of these 
elements do not always match. If so, indicate a 'buf' element such that
any top within this distance of each other should be considered the same
logical line.
default_font: The index of the font of the bulk of the text
chapter_font: The index of the font of chapter headings

Add a "title" tag for the name of the file and the title of the html
Add an "author" tag for the name of the author

SAMPLE:
<config top_margin="0" bottom_margin="10000" para_break="30" buf="5" default_font="0" />
<title>Jonathan Strange and Mr. Norrell</title>
<author>Susanna Clarke</author>
"""
from argparse import ArgumentParser
import codecs
from collections import Counter, defaultdict
import re
import sys
from xml.dom.minidom import parse

SENTENCE_END = re.compile(u'[.?!]([\'"\u201d\xbb]|\&quot;)?\s*$')
STARTS_WITH_CAP = re.compile(u'^([\'"\xab\u201c]|\&quot;)?[A-Z]')

class PDFDoc(object):
    """XML representation of a PDFDoc."""
    def __init__(self, path):
        self.path = path
        self.doc = parse(path)
        self.fonts = {}
        self.pages = {}

        self.title = text_value(self.doc, 'title') or ''
        self.html_file = u'{}.html'.format(self.title.lower().replace(u' ', u'_'))
        self.author=text_value(self.doc, 'author')
        try:
            config = self.doc.getElementsByTagName('config')[0]
            self.top_margin = int(config.getAttribute('top_margin'))
            self.bottom_margin = int(config.getAttribute('bottom_margin'))
            self.para_break = int(config.getAttribute('para_break'))
            self.buf = int(config.getAttribute('buf'))
            self.default_font = config.getAttribute('default_font')
            self.chapter_font = config.getAttribute('chapter_font')
        except:
            self.top_margin = 0
            self.bottom_margin = 0
            self.para_break = 0
            self.buf = 0
            self.default_font = None
            self.chapter_font = None

        default_font_size = 1.0
        for fontspec in self.doc.getElementsByTagName('fontspec'):
            font = Font(fontspec)
            if font.index == self.default_font:
                font.default = True
                default_font_size = float(font.size_pt)
            if font.index == self.chapter_font:
                font.chapter = True
            self.fonts[font.index] = font

        for font in self.fonts.values():
            font.size_pct = int((font.size_pt/default_font_size)*100)

    def parse(self):
        for page in self.doc.getElementsByTagName('page'):
            p = Page(page, self.fonts, self.top_margin, self.bottom_margin, self.buf)
            p.parse()
            self.pages[p.number] = p

    def write_html(self, strategy):
        """ HTML representation of the doc, written to path."""
        print 'writing', self.html_file
        with codecs.open(self.html_file, mode='wb', encoding='utf-8') as f:
            f.write(self.header)
            last_line = None
            for page in sorted(self.pages.values(), key=lambda x: x.number):
                last_top = 0
                f.write('<!-- Page {} -->\n'.format(page.number))
                for line in sorted(page.lines.values(), key=lambda x: x.top):
                    if strategy == 'vertical':
                        line_diff = line.top - last_top
                        if last_top != 0:
                            if line_diff > (2 * self.para_break):
                                f.write('<p>-<p>\n')
                            elif line.top - last_top > self.para_break:
                                f.write('<p>\n')
                        elif last_line and last_line.ends_sentence and \
                            line.begins_sentence:
                            f.write('<p>\n')
                    elif strategy == 'spaces':
                        if line.text.startswith('      '):
                            f.write('<p>\n')
                    elif strategy == 'indent':
                        if line.left > self.para_break:
                            f.write('<p>\n')
                    f.write(line.html_text)
                    f.write('\n')
                    last_top = line.top
                    last_line = line

    @property
    def header(self):
        return u"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
  "http://www.w3.org/TR/html4/strict.dtd">		
<html>
  <head>
  <meta http-equiv="content-type" content="text/html; charset=UTF-8">
<title>{title}</title>
{css}
</head>
<body>
<h1>{title}</h1>
<p class="author">by {author}

""".format(title=self.title, css=self.css, author=self.author)

    @property
    def css(self):
        css_text = '<style type="text/css">\n'
        for font in self.fonts.values():
            if font.default:
                css_text += 'body {{{}}}\n'.format(font.css_style)
            elif font.chapter:
                css_text += 'h2 {{{}}}\n'.format(font.css_style)
                css_text += '.{} {{{}}}\n'.format(font.css_class, font.css_style)
            else:
                css_text += '.{} {{{}}}\n'.format(font.css_class, font.css_style)
	css_text += 'p{text-indent:1.5em;margin:0}\n'
	css_text += 'p.section{text-indent:0;margin-top:1em}\n'
	css_text += 'p.author{text-indent:0;margin-top:1em;page-break-after:always;}\n'
        css_text += '</style>'
        return css_text

    def analyze(self):
        height_diff_ctr = Counter()
        font_ctr = Counter()
        left_ctr = Counter()
        max_length = defaultdict(lambda: 0)
        font_examples = {}
        diff_examples = {}
        left_examples = {}
        for page in self.doc.getElementsByTagName('page'):
            lines = {}
            top = 0
            for line in page.getElementsByTagName('text'):
                new_line = Line(line, self.fonts)
                if not new_line.font in font_examples:
                    font_examples[new_line.font.css_class] = new_line.text
                font_ctr[new_line.font] += 1
                if new_line.top in lines.keys():
                    old_line = lines[new_line.top]
                    if new_line.left < old_line.left:
                        old_line.text = u'{} {}'.format(new_line.text, old_line.text)
                    else:
                        old_line.text = u'{} {}'.format(old_line.text, new_line.text)
                else:
                    lines[new_line.top] = new_line
            first = True
            hold_line = None
            printed = False
            for line in sorted(lines.values(), key=lambda x: x.top):
                if not line.left in left_examples:
                    left_examples[line.left] = line.text
                left_ctr[line.left] += 1
                if line.top < 1134:
                    if first:
                        first = False
                    else:
                        diff = line.top - top
                        if not diff in diff_examples:
                            diff_examples[diff] = line.text
                        height_diff_ctr[diff] += 1
                    top = line.top
                    hold_line = line

        for k, v in height_diff_ctr.most_common(10):
            print u'diff: {:>4}  count: {:>4}  example: {}'.format(k, v, diff_examples[k])
        for k in sorted(max_length.keys()):
            print '{:>4}: {:>4}'.format(k, max_length[k])

        for k, v in left_ctr.most_common():
            if 50 < k < 100:
                print u'left: {:>4}  count: {:>4}  example: {}'.format(k, v, left_examples[k])
        for k, v in font_ctr.most_common():
            print u'font {:>8}: {:>7} {}'.format(k.css_class, v, font_examples[k.css_class])

class Page(object):
    """ Holds all the lines in a page."""
    def __init__(self, page_node, fonts, top_margin=0, bottom_margin=0, buf=5):
        """
        params:
        page_node: an xml node with the page tag
        fonts: the font list of the document
        top_margin: how many units to ignore lines within
        bottom_margin: how many units less than the page height to ignore lines within
        buf: how many units within which to consider text on the same 'line'
        """
        self.node = page_node
        self.fonts = fonts
        self.top_margin = top_margin
        self.bottom_margin = bottom_margin
        self.buf = buf

    def parse(self):
        """ Sets the number, height, and width attributes.
        Adds the line objects."""
        self.number = int(self.node.getAttribute('number'))
        self.height = int(self.node.getAttribute('height'))
        self.width = int(self.node.getAttribute('width'))
        self.lines = {}
        for n in self.node.getElementsByTagName('text'):
            line = Line(n, self.fonts)
            if not line.text.strip() or \
                    line.top < self.top_margin or \
                    line.top > self.bottom_margin:
                continue
            found = False
            for i in xrange(2*self.buf):
                key = line.top - self.buf + i
                if key in self.lines.keys():
                    found = True
                    old_line = self.lines[key]
                    old_line.add_line(line)
            if not found:
                self.lines[line.top] = CompositeLine(line)

class Font(object):
    """	
    Utility object for font specifications defined as:
    <fontspec id="0" size="16" family="Times" color="#000000"/>
    """
    def __init__(self, fontspec):
        self.fontspec = fontspec
        self.index = fontspec.getAttribute('id')
        self.size_pt = int(fontspec.getAttribute('size'))
        self.size_pct = 100
        self.family = fontspec.getAttribute('family')
        self.color = fontspec.getAttribute('color')
        self.css_class = 'class_{}'.format(self.index)
        self.default = False
        self.chapter = False

    @property
    def css_style(self):
        return 'font-family:{};font-size:{}%;color:{};'.format(self.family, self.size_pct, self.color)

class CompositeLine(object):
    def __init__(self, line):
        self.lines = [line,]
        self.top = line.top

    @property
    def left(self):
        return self.lines[0].left

    @property
    def width(self):
        return sum([l.width for l in self.lines])

    @property
    def text(self):
        text = ''
        for line in self.lines:
            text += line.text
        return text

    @property
    def html_text(self):
        text = ''
        last_right = 0
        for idx, line in enumerate(self.lines):
            if idx > 0 and last_right + 5 < line.left:
                text += ' '
            text += line.html_text
            last_right = line.left + line.width
        return text

    def add_line(self, line):
        # Don't bother adding whitespace
        if line.text.strip():
            self.lines.append(line)
            self.lines = sorted(self.lines, key=lambda x: x.left)

    @property
    def ends_sentence(self):
        return self.lines[-1].ends_sentence

    @property
    def begins_sentence(self):
        return self.lines[0].begins_sentence



class Line(object):
    CHAPTER_NUMBER = 0
    def __init__(self, line, fonts):
        self.line = line
        self.top = int(line.getAttribute('top'))
        self.left = int(line.getAttribute('left'))
        self.width = int(line.getAttribute('width'))
        self.font = fonts[line.getAttribute('font')]
        self.text = ''
        for c in line.childNodes:
            try:
                self.text += c.toxml()
            except:
                print 'exception'
                pass

    @property
    def html_text(self):
        if self.font.default:
            return self.text
        elif self.font.chapter:
            Line.CHAPTER_NUMBER += 1
            return u'<h2>{} {}</h2>'.format(self.text, Line.CHAPTER_NUMBER)

        else:
            return u'<span class="{}">{}</span>'.format(self.font.css_class, self.text)

    @property
    def ends_sentence(self):
        return SENTENCE_END.search(self.text.strip())

    @property
    def begins_sentence(self):
        return STARTS_WITH_CAP.search(self.text.strip())

def text_value(parent, child_tag):
    """ Returns text value of first child tag of parent."""
    for n in parent.getElementsByTagName(child_tag):
        return n.firstChild.nodeValue

def analyze(path):
    doc = PDFDoc(path)
    doc.analyze()

def write_html(path, strategy):
    doc = PDFDoc(path)
    doc.parse()
    doc.write_html(strategy)

if __name__ == '__main__':
    parser = ArgumentParser(description='Convert pdf2xml to html')
    parser.add_argument('file_path', type=str)
    parser.add_argument('-action', type=str, default='a',
                        help='"a" for analyze, anything else for write')
    parser.add_argument('-strategy', type=str, default='vertical',
                        help='"vertical", "spaces", or "indent" para breaks')
    args = parser.parse_args()

    if args.action == 'a':
        analyze(args.file_path)
    else:
        write_html(args.file_path, args.strategy)

