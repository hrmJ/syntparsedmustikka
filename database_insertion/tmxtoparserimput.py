#! /usr/bin/env python
#Import modules{{{1
#For unicode support:{{{2
import codecs
import sys
#2}}}
#xml parsing{{{2
from lxml import etree
#2}}}
#1}}}
#Main module{{{1
def main():
    try:
        sourcefile = sys.argv[1]
        languages = sys.argv[2:]
    except:
        print('Usage: {} <path to source tmx> <language> ... <language n>'.format(sys.argv[0]))
        sys.exit(0)
    with codecs.open(sourcefile, encoding="utf-8") as f:
        xmlstring = f.read()
    #Create an lxml etree object of the string
    root = etree.fromstring(xmlstring)
    for language in languages:
        xpathq = "//tuv[@xml:lang='{}']//seg".format(language)
        segs = root.xpath(xpathq)
        preparedinput = ""
        for seg in segs:
            preparedinput += "\n!!!!\n" + seg.text
        f = open('{}_{}.prepared'.format(sourcefile,language), 'w')
        f.write(preparedinput.strip())
        f.close()
#1}}}
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
