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
        language = sys.argv[2]
    except:
        print('Usage: {} <path to source tmx> <language>'.format(sys.argv[0]))
        sys.exit(0)
    with codecs.open(sourcefile, encoding="utf-8") as f:
        xmlstring = f.read()
    #Create an lxml etree object of the string
    root = etree.fromstring(xmlstring)
    xpathq = "//tuv[@xml:lang='{}']//seg".format(language)
    segs = root.xpath(xpathq)
    preparedinput = ""
    for seg in segs:
        preparedinput += "\n#\n" + seg.text
    f = open('preparedoutput.txt', 'w')
    f.write(preparedinput.strip())
    f.close()
#1}}}
#Start the script{{{1
if __name__ == "__main__":
    main()
#1}}}
