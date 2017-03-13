from dbmodule import psycopg

con = psycopg("araneum_fi",'juho')

sids = con.FetchQuery("SELECT DISTINCT sentence_id FROM fi_conll WHERE sentence_id > 1199689")
for sid in sids:
    con.query("INSERT INTO groups (name, sentence_id, corpus) values(%s, %s, %s)", ("lc1b",sid[0],"araneum"),commit=True)
