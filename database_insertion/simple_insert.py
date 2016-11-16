import sys
import re
from insert_pair import TrimList, Bar, psycopg, AddRow, TextPair, GetLastValue
import glob
import logging
import time

class InsData():
    def __init__(self, conllfile, metadatafile, dbname, lang, groupname='',corpusname=''):
        self.table = lang + '_conll'
        self.con = psycopg(dbname,'juho')
        self.groupname = groupname
        self.corpusname = corpusname
        self.GetMeta(metadatafile)
        with open(conllfile,'r') as f:
            self.conllinput = f.read()

    def GetMeta(self,fname):
        print('Fetching old references from db')
        oldmeta = self.con.FetchQuery('SELECT DISTINCT title from text_ids',flatten=True)
        print('Now collecting the new references...')
        refdicts = list()
        self.reflist = list()
        titlelist = list()
        with open(fname,'r') as f:
            for idx, ref in enumerate(f):
                ref = ref.strip()
                self.reflist.append(ref)
                if ref not in oldmeta and ref not in titlelist:
                    refdicts.append({'title':ref})
                if ref not in titlelist:
                    titlelist.append(ref)
                if idx % 1000 == 0:
                    print(idx)
        #insert the new metadata
        if refdicts:
            print('Inserting new {} references to db...'.format(len(refdicts)))
            logging.info('Inserting new {} references to db...'.format(len(refdicts)))
            self.con.BatchInsert('text_ids', refdicts)

        #Finally, get all NECESSARY metadata to two separate lists
        print('Querying to get the indices for the references needed here...')
        self.metadata = self.con.FetchQuery('SELECT DISTINCT title, id from text_ids WHERE title in %(titles)s order by id',{'titles':tuple(titlelist)},usedict=True)
        print('Qyuery done, using {} references'.format(len(self.metadata)))
        self.titles = list()
        self.textids = list()
        for metarow in self.metadata:
            self.titles.append(metarow['title'])
            self.textids.append(metarow['id'])

    def PrepareConllToDb(self):
        self.segments = TrimList(re.split(TextPair.splitpattern,self.conllinput))
        if len(self.segments)!=len(self.reflist):
            try:
                logging.info("Ups! Tyhjiä segmenttejä tms. havaittu ryhmässä {}, tarkista esimerkiksi seuraava kohta:\n\n {} \n\n ".format(self.groupname, self.segments[self.segments.index('')-1]))
            except ValueError:
                lengths = [len(item) for item in self.segments]
                min_idx = [idx for idx, item in enumerate(self.segments) if len(item)==min(lengths)]
                logging.info("OHO! Joku isompi ongelma, joka johtuu siitä, että eri määrä segmenttejä ({} kpl)ja viitteitä ({}) ryhmässä {}. Tarkista esimerkiksi seuraava kohta:\n\n {}".format(len(self.segment), len(self.reflist), self.groupname, self.segments[min_idx[0]-1] ))
                import ipdb; ipdb.set_trace()
            return False
        #Notice that +1 is added to the maximal sentence value
        sentence_id = GetLastValue(self.con.FetchQuery("SELECT max(sentence_id) FROM {}".format(self.table))) + 1
        last_segment_idx    = GetLastValue(self.con.FetchQuery("SELECT max(align_id) FROM {}".format(self.table)))
        self.rowlist = list()
        self.groupnamelist = list()
        bar=Bar('Reading the conll input...',max=int(len(self.segments)/100))
        logging.info("Started {}".format(self.groupname))
        starttime = time.time()
        for segment_idx, segment in enumerate(self.segments):
            align_id = last_segment_idx + segment_idx + 1
            for word in segment.splitlines():
                #read all the information about the word
                if word == '':
                    #empty lines are sentence breaks
                    sentence_id += 1
                    self.groupnamelist.append({'name': self.groupname,'sentence_id': sentence_id, 'corpus':self.corpusname})
                else:
                    columns = word.split('\t')
                    #0 is for "translation_id" that doesn't exist for momolingual files
                    try:
                        self.rowlist.append(AddRow(columns, align_id, sentence_id, self.GetTextId(self.reflist[segment_idx]), self.table, 0))
                    except IndexError:
                        #hacky! just using the previous reference if the reflist is 1 line too long
                        self.rowlist.append(AddRow(columns, align_id, sentence_id, self.GetTextId(self.reflist[-1]), self.table, 0))
                        print('some problem with the number of segments and the number of references...')
                        logging.info('some problem with the number of segments and the number of references...')
            if segment_idx % 100 == 0:
                try:
                    bar.next()
                except ZeroDivisionError:
                    print('The progress bar cannot be moved at segment idx number {}'.format(segment_idx))

        logging.info("Finished {} in {} seconds".format(self.groupname, time.time()-starttime))
        bar.finish()
        return True

    def GetTextId(self, title):
        try:
            return self.textids[self.titles.index(title)]
        except IndexError:
            return 0

    def InsertToDb(self):
        """Make the actual connection to tb"""
        #limit the amount of items to be inserted at once
        rowportions = list()
        itemlimit=200000
        start = 0
        end = itemlimit
        while len(self.rowlist)-end>0:
            rowportions.append(self.rowlist[start:end])
            end += itemlimit
            start += itemlimit
        if rowportions:
            rowportions.append(self.rowlist[start:])
        else:
            rowportions.append(self.rowlist)

        #actual insertion:
        print('starting to insert in {} portions'.format(len(rowportions)))
        for portion in rowportions:
            print('\nInserting to table {}, this might take a while...'.format(self.table))
            self.con.BatchInsert(self.table, portion)
            print('Inserted {} rows.'.format(self.con.cur.rowcount))
        print('Now updating the group code.')
        self.con.BatchInsert('groups', self.groupnamelist)
        print('Inserted {} rows.'.format(self.con.cur.rowcount))


logging.basicConfig(format='%(asctime)s %(message)s', filename='insertionlog.txt',level=logging.DEBUG)
isbulk = False

if (sys.argv[1]=="bulk"):
    #Olettaa, että kaikki syötettävät tiedostot kansiossa, niin että nimetty tyylillä:
    #lc0a   lc0a.sources
    #lc0b   lc0b.sources
    #jne.
    logging.info("START")
    wholestarttime = time.time()
    #sys.exit('Usage: {} <BULK> <path to folder> <dbname> <lang> <corpus name>'.format(sys.argv[0]))
    con = psycopg(sys.argv[3],'juho')
    previousinstances = con.FetchQuery('SELECT DISTINCT name FROM groups',flatten=True)
    isbulk = True

    for filename in glob.glob(sys.argv[2] + "*"):

        if 'sources' not in filename:
            starttime = time.time()
            groupname = filename
            if ("/" in filename):
                groupname = filename[filename.rfind("/")+1:]
            if groupname not in previousinstances:
                print('STARTING to insert {}'.format(groupname))
                #conllfile, metadatafile,        dbname,       lang,      groupname='',corpusname=''):
                thisdata = InsData(*[filename, filename + ".sources", sys.argv[3], sys.argv[4], groupname, sys.argv[5]])
                if thisdata.PrepareConllToDb():
                    thisdata.InsertToDb()
                else:
                    logging.info('SKIPPING {} because of inconsistencies'.format(groupname))

    print('ALL Done')
    logging.info("Finished everything in {} seconds".format(time.time()-wholestarttime))

elif (len(sys.argv)<5):
    sys.exit('Usage: {} <conllinput> <references> <dbname> <lang> <groupname> <corpus name>'.format(sys.argv[0]))


if not isbulk:
    thisdata = InsData(*sys.argv[1:])
    if thisdata.PrepareConllToDb():
        thisdata.InsertToDb()
    else:
        logging.info('SKIPPING {} because of inconsistencies'.format(thisdata.groupname))
