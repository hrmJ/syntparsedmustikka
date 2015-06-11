#! /usr/bin/env python
from deptypetools import  LogNewDeprel, simpleupdate, makeSearch, log, DependentToHead, DependentSameAsHead
from interface import printResults

def gdep(dbcon=False):
    """"Aluksi määritellään kaikkien elementtien luokaksi gdep, jota sitten
    tarkennetaan niin pitkälle kuin mahdollista    """

    LogNewDeprel('Create the category of gdep in the TDT data')
    dbcon.query('UPDATE fi_conll SET contr_head = head, contr_deprel = %(contrdep)s',{'contrdep':'gdep'})
    log('The gdep category was succesfully created')

def obj(dbcon=False):
    """Nimetään uudelleen dobj-kategoria obj:ksi
    
    Tapaukset, joissa sain hänet itkemään -lauseen *hänet* on nsubj
    -------------------------------------------------------------
    (infinitiivistä riippuvat nsubj)
    - nsubj > obj
    
    """

    #1. Uudelleennimeäminen
    LogNewDeprel('Create the category of obj in the TDT data')
    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdep)s WHERE deprel = %(deprel)s',{'contrdep':'obj','deprel':'dobj'})
    log('Succesfully renamed dobj to obj')
    #2. Infinitiivien subjektit, jotka voisi luokitella obj
    thisSearch = makeSearch(database='syntparrus', dbtable='fi_conll', ConditionColumns={'?feat':'%CASE_Acc%'}, headcond={'column':'deprel','values': ('iccomp',)})
    DependentSameAsHead(dbcon=dbcon,thisSearch=thisSearch, dbtable='fi_conll', matchdep='obj')

def advmod(dbcon=False):
    """ Muokkaan SN-jäsennyksen obst-kategoriaa ja
    TDT-jäsennyksen advmod-kategoriaa siten, että kontrastiiviseen jäsennykseen
    luodaan oma advmod-luokkansa. Tähän luokkaan rajataan SN-jäsennyksestä ne
    obst-kategorian sanat, joiden sanaluokka on adverbi (ja jotka
    automaattisesti ovat myös verbin dependenttejä) ja TDT-jäsennyksestä ne
    advmod-kategorian sanat, jotka ovat verbin dependenttejä.
    """

    LogNewDeprel('Create the advmod category in tdt')
    thisSearch = makeSearch(database='syntparrus', dbtable='fi_conll', ConditionColumns={'deprel':('advmod',),'pos':('Adv',)}, headcond={'column':'pos','values': ('V',)})
    simpleupdate(thisSearch,dbcon,deprel='advmod')

def infcomp(dbcon=False):
    """Muokkaan kontrastiivista analyysikerrosta varten SN-analyysiä siten,
    että verbillä ilmaistavat subjektit luokitellaan uudella tunnisteella
    infcomp (tarkemmin ks. kohta x). Tähän kategoriaan luetaan myös kaikki
    infinitiivimuotoiset13 sanat, jotka TDT:ssä on luokiteltu
    lausesubjekteiksi, joko kategoriaan csubj tai csubj-cop.

    Kuten nesessiivilauseiden osalta, tukeudun myös apuverbien kohdalla
    SN-analyysin mukaiseen malliin ja määrittelen kontrastiivisessa
    analyysikerroksessa pääsanaksi apuverbin ja dependentiksi pääverbin. Tästä
    seuraa, että apuverbin dependenssityyppi on joko ROOT tai jokin sivu- tai
    rinnasteisen lauseen pääsanan kategoria, jolloin pääverbille on erikseen
    määriteltävä oma kategoriansa -- tällaiseksi soveltuu edellä SN-aineiston
    infinitiivisubjektien yhteydessä määritelty infcomp-luokka. TDT-analyysin
    kannalta tämä tarkottaa sitä, että kieltoverbien kantama informaatio lauseen
    kielteisyydestä katoaa kontrastiivisesta analyysikerroksesta. Myös TDT:n aux-,
    auxpass- ja SN:n analit-kategoriat poistuvat.


    Kopulat!
    ---------

    on pakko-tyyppisissä tapauksissa kopula pitää ehkä jättää kontrastiiviseen tasoon niin kuin
    se on Haverinen 57, esim. 179

    """

    LogNewDeprel('Create the category of infcomp in the TDT data')
    #1. iccomp-tapaukset vain nimetään uudelleen infcomp:ksi
    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdep)s WHERE deprel = %(deprel)s ',{'contrdep':'infcomp','deprel':('iccomp')})
    #2. aux-tapauksissa riippuvuussuunta pitää kääntää
    thisSearch = makeSearch(database='syntparrus',dbtable='fi_conll',  ConditionColumns={'deprel':('aux',)})
    DependentToHead(dbcon=dbcon,thisSearch=thisSearch,dbtable='fi_conll',matchdep='head',headdep='infcomp')
    #3. Infinitiivimuotoiset Csubj-cop ja csubj (haverinen esim. 182)
    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdep)s WHERE deprel IN %(deprel)s AND feat LIKE %(feat)s',{'contrdep':'infcomp','deprel':('csubj-cop','csubj'),'feat':'%INF_Inf1'})

def semsubj(dbcon=False):
    """Otan kontrastiivista analyysikerrosta varten käyttöön termin semsubj
    (vrt. Leinonen 1985: 15) nesessiivilauseille ja muille vastaaville
    rakenteille, joissa SN-analyysi määrittää infinitiivimuotoisen verbin
    subjektiksi.
    
    Näin TDT:n nsubj ja ... muuttuvat näiden lauseiden osalta kontrastiivisessa
    kerroksessa muotoon semsubj. 
    
    Rakenteen finiittimuotoinen verbi katsotaan SN-jäsennyksen mukaisesti
    juureksi ja infinitiivimuotoinen verbi luetaan infcomp-kategoriaan.

    On huomattava, että TDT-aineistossa myös substantiivin
    määritteet saattavat olla genetiivimuotoisia ja saada nsubj-kategorian. Näitä
    ei kontrastiivisessa jäsennyksessä lueta semsubj-kategoriaan.

    ks. Haverinen 62

    On huomioitava myös tapaukset, joissa ei ole genetiivimuotoista nsubjektia!

    """
    LogNewDeprel('Create the semsubj category in SN')
    thisSearch = makeSearch(database='syntparrus',dbtable='fi_conll',  ConditionColumns={'deprel':('nsubj',),'?feat':'%CASE_Gen%'},headcond={'column':'pos','values':('V',)})
    simpleupdate(thisSearch, dbcon, deprel='semsubj')

def prdctv(dbcon=False):
    """Tämä tarkoittaa käytännössä sitä, että TDT-jäsennetyn aineiston
    nsubj-cop-tapaukset luokitellaan tavallisiksi nominisubjekteiksi (nsubj) ja

    sekä niiden että predikatiivina olevan sanan pääsanaksi vaihdetaan sana,
    joka alun perin on analysoitu kategorialla cop. Kopulan dependenssityypiksi
    siirretään se tyyppi, johon predikatiivi oli luokiteltu.


    Haverinen 32:

    - The basic alternatives for predicatives are nominals 
    (nouns, adjectives, pro- nouns and numerals). 
    
    - Words of these parts-of-speech are required to be in nomi-
    native, partitive or genitive to be accepted as predicatives.

    """

    LogNewDeprel('Create the prdctv category in tdt')
    thisSearch = makeSearch(database='syntparrus', dbtable='fi_conll', ConditionColumns={'deprel':('nsubj-cop',)})
    log('Change nsubj-cop to nsubj')
    #simpleupdate(thisSearch,dbcon,deprel='nsubj')
    #Update the contrastive layer for nsubj-cop and cop
    updated = 0
    for key, matchlist in thisSearch.matches.items():
        for match in matchlist:
            try:
                prdctv = match.matchedsentence.words[match.matchedword.head]
                match.matchedword.tokenid
                cop = False
                match.matchedsentence.listDependents(match.matchedword.head)
                for dep in match.matchedsentence.dependentlist:
                    if dep.deprel == 'cop':
                        cop = dep
                if not cop:
                    #If the nsubj-cop's head has no cop as its dependent, look in the entire sentence
                    for key, dep in match.matchedsentence.words.items():
                        if dep.deprel == 'cop':
                            cop = dep
                if cop:
                    #predicative's and nsubj-cop's new head
                    dbcon.query('UPDATE fi_conll SET contr_head = %(contrhead)s WHERE id IN %(idlist)s',{'contrhead':cop.tokenid,'idlist':(match.matchedword.dbid,prdctv.dbid)})
                    #copula's new deprel
                    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdeprel)s WHERE id = %(idlist)s',{'contrdeprel':prdctv.deprel,'idlist':cop.dbid})
                    updated += 1
                    print('{}/{}'.format(updated,len(thisSearch.matches)), end='\r')
                else:
                    #If no copula at all
                    log('No copula in sid {}'.format(match.matchedsentence.sentence_id))
            except KeyError:
                log('KeyError')
    print('\n'*2)
    log('Updated {} prdctv-related entries'.format(updated))


def nsubj(dbcon=False):
    """nsubj
    """
    LogNewDeprel('Create the category of infcomp in the TDT data')
    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdep)s WHERE deprel IN %(deprel)s AND contr_deprel = %(oldcontrdep)',{'contrdep':'nsubj','oldcontrdep':'gdep','deprel':('csubj','csubj-cop')})
    log('Succesfully renamed dobj to obj')

def cop(dbcon=False):
    """Suomen kielen kopulallisten nesessiivilauseiden (ks. esimerkki @eeekopula),
    osalta kontrastiivinen jäsennys rakennetaan predikatiivirakenteesta
    poikkeavalla tavalla niin, että kopulan kategoria säilytetään ja niin kopula
    kuin infinitiivimuoto katsotaan lauseen keskeisen nominin dependenteiksi. Tämä
    jäsennystapa sopii yhteen sen kanssa, miten SN-aineistossa usein analysoidaan
    vastaavantyyppisiä rakenteita."""

    LogNewDeprel('Create the cop category in tdt')
    thisSearch = makeSearch(database='syntparrus', dbtable='fi_conll', ConditionColumns={'deprel':('cop',),'contr_dep':('gdep',)})
    simpleupdate(thisSearch,dbcon,deprel='cop')
