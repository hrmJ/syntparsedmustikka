import sys
import re
from insert_pair import TrimList, Bar, psycopg, AddRow, TextPair, GetLastValue

class InsData():
    def __init__(self, conllfile, metadatafile, dbname, lang):
        self.table = lang + '_conll'
        self.con = psycopg(dbname,'juho')
        self.GetMeta(metadatafile)
        with open(conllfile,'r') as f:
            self.conllinput = f.read()

    def GetMeta(self,fname):
        print('Fetching old references from db')
        oldmeta = self.con.FetchQuery('SELECT DISTINCT title from text_ids',flatten=True)
        print('Now collecting the new references...')
        refdicts=list()
        self.reflist = list()
        with open(fname,'r') as f:
            for idx, ref in enumerate(f):
                ref = ref.strip()
                self.reflist.append(ref)
                if ref not in oldmeta:
                    refdicts.append({'title':ref})
                if idx % 1000 == 0:
                    print(idx)
        
        #insert the new metadata
        if refdicts:
            print('Inserting references to db...')
            self.con.BatchInsert('text_ids', refdicts)

        #Finally, get all metadata to two separate lists
        self.metadata = self.con.FetchQuery('SELECT title, id from text_ids order by id',usedict=True)
        self.titles = list()
        self.textids = list()
        for metarow in self.metadata:
            self.titles.append(metarow['title'])
            self.textids.append(metarow['id'])

    def PrepareConllToDb(self):
        self.segments = TrimList(re.split(TextPair.splitpattern,self.conllinput))
        sentence_id = GetLastValue(self.con.FetchQuery("SELECT max(sentence_id) FROM {}".format(self.table)))
        last_segment_idx    = GetLastValue(self.con.FetchQuery("SELECT max(align_id) FROM {}".format(self.table)))
        self.rowlist = list()
        bar=Bar('Reading the conll input...',max=int(len(self.segments)/100))
        for segment_idx, segment in enumerate(self.segments):
            align_id = last_segment_idx + segment_idx + 1
            for word in segment.splitlines():
                #read all the information about the word
                if word == '':
                    #empty lines are sentence breaks
                    sentence_id += 1
                else:
                    columns = word.split('\t')
                    #0 is for "translation_id" that doesn't exist for momolingual files
                    self.rowlist.append(AddRow(columns, align_id, sentence_id, self.GetTextId(self.reflist[segment_idx]), self.table, 0))
            if segment_idx % 100 == 0:
                bar.next()

        bar.finish()

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

if (len(sys.argv)<5):
    sys.exit('Usage: {} <conllinput> <references> <dbname> <lang>'.format(sys.argv[0]))

thisdata = InsData(*sys.argv[1:])
thisdata.PrepareConllToDb()
thisdata.InsertToDb()
