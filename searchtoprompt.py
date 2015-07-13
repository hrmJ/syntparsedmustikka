import pickle
import glob
from menus import multimenu
from interface import MainMenu
import search
import dbmodule

#Load the saved search from pickle
menu = MainMenu()
menu.viewsavedsearches()
#Fetch all the source lemmas
mySearch = search.Search.all_searches[0]

