import csv

class Csvlist:
    def __init__(self,csvpath):
        with open(csvpath, 'r') as f:
            self.aslist = list(csv.reader(f))

def joinidlist(idrows):
    """Flatten the lists from database"""
    idlist =  list(itertools.chain(*idrows))
    idlist = ','.join(map(str, idlist)) 
    return idlist
