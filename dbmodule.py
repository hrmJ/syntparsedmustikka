#! /usr/bin/env python
#psql integration:{{{2
import psycopg2
import psycopg2.extras
from psycopg2.extensions import AsIs
#Classes{{{1
#Vkdatabase{{{2
class Vkdatabase:
    """Establish a connection to the vk2 database and create two cursors for use"""
    #initialize {{{3
    def __init__(self):
       self.connection = psycopg2.connect("dbname='vk2' user='juho'")
       self.connection.autocommit = True
       self.dictcur = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
       self.cur = self.connection.cursor()
    #INSERT query{{{3
    def insertquery(self, SQL, valuetuple=("empty",)):
        try:
            self.cur.execute(SQL, valuetuple)
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))
    #Query with a dictionary cursor {{{3
    def dictquery(self, SQL,valuetuple=("empty",)):
        try:
            self.dictcur.execute(SQL, valuetuple)
            return self.dictcur.fetchall()
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))
    #Query with a non-dictionary cursor {{{3
    def nondictquery(self, SQL,valuetuple=("empty",)):
        try:
            self.cur.execute(SQL, valuetuple)
            return self.cur.fetchall()
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print(SQL)
            print ("Psql gives the error: {}".format(e.pgerror))

class mydatabase:
    """Establish a connection to database and create two cursors for use"""
    #initialize {{{3
    def __init__(self,dbname,username):
       self.connection = psycopg2.connect("dbname='{}' user='{}'".format(dbname, username))
       self.connection.autocommit = True
       self.dictcur = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
       self.cur = self.connection.cursor()
    #INSERT query{{{3
    def insertquery(self, SQL, valuetuple=("empty",)):
        try:
            self.cur.execute(SQL, valuetuple)
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))
    #Query with a dictionary cursor {{{3
    def dictquery(self, SQL,valuetuple=("empty",)):
        try:
            self.dictcur.execute(SQL, valuetuple)
            return self.dictcur.fetchall()
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print ("Psql gives the error: {}".format(e.pgerror))
    #Query with a non-dictionary cursor {{{3
    def nondictquery(self, SQL,valuetuple=("empty",)):
        try:
            self.cur.execute(SQL, valuetuple)
            return self.cur.fetchall()
        except psycopg2.Error as e:
            print("Somerthing wrong with the query")
            print(SQL)
            print ("Psql gives the error: {}".format(e.pgerror))
