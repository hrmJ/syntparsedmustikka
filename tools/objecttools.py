import pickle, gzip

def savepickle(filename, *objects):
    ''' save objects into a compressed diskfile '''
    fil = gzip.open(filename, 'wb')
    for obj in objects: pickle.dump(obj, fil)
    fil.close( )

def loadpickle(filename):
    ''' reload objects from a compressed diskfile '''
    fil = gzip.open(filename, 'rb')
    while True:
        try: return pickle.load(fil)
        except EOFError: break
    fil.close( )
