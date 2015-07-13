import pickle
import glob
from menus import multimenu
from interface import MainMenu
import search

#Load the saved search from pickle
menu = MainMenu()
menu.viewsavedsearches()
tmeSearch = search.Search.all_searches[0]

