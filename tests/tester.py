import sys
scriptdir = '/home/juho/corpora2/syntparsedmustikka/'
sys.path.append(scriptdir)
import interface

testmenu = interface.MainMenu()
testmenu.selecteddb = 'syntparfin2'
interface.Db.con = interface.mydatabase(testmenu.selecteddb,'juho')
interface.Db.searched_table = 'fi_conll'
testmenu.selectedlang = 'fi'

#Concordancing:

#testmenu.runmenu()
testmenu.conditionset = interface.ConditionSet(testmenu.selecteddb)
#testmenu.conditionset.FormatOptionString()
testmenu.Parconc()

#cset = testmenu.conditionset
#val = cset.columns[6].PickSearchValue()

print('Test performed')
