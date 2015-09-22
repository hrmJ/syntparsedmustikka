#! /usr/bin/env python
from deptypetools import  LogNewDeprel, simpleupdate, makeSearch, log, DependentToHead, DependentSameAsHead, DepTypeUpdater
import deptypetools
from interface import printResults
import rel_tdt
import os.path

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

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the category of obj in the TDT data')
    #2. Nimeä dobj obj:ksi
    updater.rename('dobj','obj')
    #2. Infinitiivien subjektit, jotka voisi luokitella obj
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'?feat':'%CASE_Acc%'}, headcond={'column':'deprel','values': ('iccomp',)})
    updater.Update(updateType='DependentOfSameAsHead',matchdep='obj', message='Making subjects of infinitives objects of the finite verb..')

def rel(dbcon=False):
    """
    HUOM! joten-sana kohdeltava erikseen

    """

    LogNewDeprel('REANALYZE the rel category in TDT')

    log('1. Search for all the relative pronouns  analyzed as "rel"'.format(dbcon.dbname))
    thisSearch = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('rel',),'lemma':('joka','mikä')})

    log('2. Extract the relative clauses')
    relclauses = rel_tdt.getRelDict(thisSearch)

    log('3. Print the relative clauses to file')
    rel_tdt.PrintRelClausesToFile(relclauses)

    #Reparse, if not yet done
    reparsedfile = "{}_reparsedrelativizers.conll".format(dbcon.dbname)
    if not os.path.isfile(reparsedfile):
        #if no previous reprse found:
        log('Now re-parse. This should take at least 10 mins ')
        os.system("cat parserinput.txt | /home/juho/Dropbox/VK/skriptit/python/finnish_dep_parser/Finnish-dep-parser/parser_wrapper.sh > {}".format(reparsedfile))

    log('4. Read the new deprels from the reparsed file')
    newdeprels = rel_tdt.ReadConllInput(reparsedfile)

    log('5. Insert the new deprels to the database')
    rel_tdt.UpdateContrRel(dbcon, relclauses, newdeprels)

def nommod(dbcon=False):
    """

    Säilytetään TDT:n nommod- ja nommod-own-kategoriat sellaisinaan
    
    """

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the category of nommod and nommod-own in the TDT data')
    updater.UseOriginals(('nommod','nommod_own','punct','nsubj', 'ROOT'))

def advmod(dbcon=False):
    """ Muokkaan SN-jäsennyksen obst-kategoriaa ja
    TDT-jäsennyksen advmod-kategoriaa siten, että kontrastiiviseen jäsennykseen
    luodaan oma advmod-luokkansa. Tähän luokkaan rajataan SN-jäsennyksestä ne
    obst-kategorian sanat, joiden sanaluokka on adverbi (ja jotka
    automaattisesti ovat myös verbin dependenttejä) ja TDT-jäsennyksestä ne
    advmod-kategorian sanat, jotka ovat verbin dependenttejä.

    *juuri niin* -tapaukset: kun pääsana ei verbi ... attr?
    """

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the category of advmod  in the TDT data')
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('advmod',),'pos':('Adv',)}, headcond={'column':'pos','values': ('V',)})
    updater.simpleupdate(deprel='advmod')

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

    *on pakko*-tyyppisissä tapauksissa kopula pitää ehkä jättää kontrastiiviseen tasoon niin kuin
    se on Haverinen 57, esim. 179

    Subjektin pääsana?
    ------------------

    ks. github #22

    Riippuvuusketjut muuttuvat ongelmallisiksi, jos on useampi infinitiiviriippuvuus
    samassa lauseessa!!!
    Mahdollisesti ratkaisua 
    - päivittäessä tarkistaa tämän erikseen
    - tempdeprel-kerros
    - dbid contr_deprel-listassa
    - muita..

    TOISTAISEKSI pidetään pienempi paha, ja annetaan muiden riippuvuuksien edelleen
    olla kiinni PÄÄVERBISSÄ. Tämä on lopulta vertailun mahdollistava ratkaisu, kun SN-
    analyysissa ei useinkaan ole apuverbiä siinä missä se on tdt:ssä


    """

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the category of infcomp in the TDT data')
    #1. iccomp- ja xcomp-tapaukset vain nimetään uudelleen infcomp:ksi
    #updater.rename(('iccomp','xcomp'),'infcomp',oldaslist=True)
    #2. neg, aux- ja auxpass-tapauksissa riippuvuussuunta pitää kääntää
    updater.search = makeSearch(database=dbcon.dbname,dbtable='fi_conll',  ConditionColumns={'deprel':('auxpass','aux','neg')})
    updater.Update(updateType='DependentBecomesHead', headdep='infcomp')
    #3. Infinitiivimuotoiset Csubj-cop ja csubj (haverinen esim. 182)
    updater.updateByQuery(contr_deprel = 'infcomp', where='deprel IN %(deprel)s AND feat LIKE %(feat)s', valuedict={'deprel':('csubj-cop','csubj'),'feat':'%INF_Inf1'}, message='Making csubj-cop and csubj infcomp')

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
    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the semsubj category in SN')
    updater.search = makeSearch(database=dbcon.dbname,dbtable='fi_conll',  ConditionColumns={'deprel':('nsubj',),'?feat':'%CASE_Gen%'},headcond={'column':'pos','values':('V',)})
    updater.simpleupdate(deprel='semsubj')

def prdctv(dbcon=False):
    """Tämä tarkoittaa käytännössä sitä, että TDT-jäsennetyn aineiston
    nsubj-cop-tapaukset luokitellaan tavallisiksi nominisubjekteiksi (nsubj) ja

    sekä niiden että predikatiivina olevan sanan pääsanaksi vaihdetaan sana,
    joka alun perin on analysoitu kategorialla cop. Kopulan dependenssityypiksi
    siirretään se tyyppi, johon predikatiivi oli luokiteltu.

    Jää monia nsibj-cop-tapauksia, joiden lauseessa ei ole kopulaa

    Haverinen 32:

    - The basic alternatives for predicatives are nominals 
    (nouns, adjectives, pro- nouns and numerals). 
    
    - Words of these parts-of-speech are required to be in nomi-
    native, partitive or genitive to be accepted as predicatives.

    ongelma: apuverbien ketjut.

    """

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the prdctv category in tdt')
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('nsubj-cop',)})
    log('Change nsubj-cop to subj')
    #Change the deprel of nsubj-cop to always be nsubj
    updater.simpleupdate(deprel='nsubj')
    #Update the contrastive layer for nsubj-cop and cop
    nocopula = list()
    contr_heads = list()
    contr_deprels = list()
    for key, matchlist in updater.search.matches.items():
        for match in matchlist:
            try:
                prdctv = match.matchedsentence.words[match.matchedword.head]
                match.matchedword.tokenid
                nsubjcop = match.matchedword
                match.matchedsentence.listDependents(match.matchedword.head)
                cop = False
                for dep in match.matchedsentence.dependentlist:
                    if dep.deprel == 'cop':
                        cop = dep
                if not cop:
                    #If the nsubj-cop's head has no cop as its dependent, look in the entire sentence
                    for key, dep in match.matchedsentence.words.items():
                        if dep.deprel == 'cop':
                            cop = dep
                if cop:
                    #Set the new heads:
                    contr_heads.append({'baseval':nsubjcop.dbid,'changedval':cop.tokenid})
                    contr_heads.append({'baseval':prdctv.dbid,'changedval':cop.tokenid})
                    contr_heads.append({'baseval':cop.dbid,'changedval':prdctv.head})
                    #Set the new deprels:
                    contr_deprels.append({'baseval':prdctv.dbid, 'changedval' : 'prdctv'})
                    contr_deprels.append({'baseval':cop.dbid, 'changedval' : prdctv.deprel})
                else:
                    #If no copula at all
                    nocopula.append(str(match.matchedsentence.sentence_id))
            except KeyError:
                log('KeyError')
    updates = [{'updatedcolumn':'contr_deprel','basecolumn':'id','valuelist':contr_deprels},
               {'updatedcolumn':'contr_head','basecolumn':'id','valuelist':contr_heads}]
    dbcon.BatchUpdate(table='fi_conll', updates=updates)
    log('This might potentially effect {} database rows.'.format(dbcon.cur.rowcount))
    log('Sentences {} contain no copula'.format(','.join(nocopula)))

def nsubj(dbcon=False):
    """nsubj
    VAATII huomiota!
    """
    LogNewDeprel('Create the category of nsubj in the TDT data')
    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdep)s WHERE deprel IN %(deprel)s AND contr_deprel = %(oldcontrdep)s',{'contrdep':'nsubj','oldcontrdep':'gdep','deprel':('csubj','csubj-cop')})
    log('Succesfully renamed csubj-cop and csubj to nsubj')

def cop(dbcon=False):
    """Suomen kielen kopulallisten nesessiivilauseiden (ks. esimerkki @eeekopula),
    osalta kontrastiivinen jäsennys rakennetaan predikatiivirakenteesta
    poikkeavalla tavalla niin, että kopulan kategoria säilytetään ja niin kopula
    kuin infinitiivimuoto katsotaan lauseen keskeisen nominin dependenteiksi. Tämä
    jäsennystapa sopii yhteen sen kanssa, miten SN-aineistossa usein analysoidaan
    vastaavantyyppisiä rakenteita."""

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the cop category in tdt')
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('cop',),'contr_deprel':('gdep',)})
    updater.simpleupdate(deprel='cop')

def prtcl(dbcon=False):
    """
    TDT-jäsennyksessä fraasinomaisesti pääverbiinsä liittyvät partikkelit on
    jäsennetty erilliseen prt-kategoriaansa. Myös nämä liitetään osaksi
    kontrastiivisen analyysin prtcl-luokkaa.
    """

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the prtcl category in TDT')
    updater.search = makeSearch(database=dbcon.dbname, dbtable = 'fi_conll', ConditionColumns={'deprel':('prt',)})
    updater.simpleupdate(deprel='prtcl')

def cdep(dbcon=False):
    """
    Otan kontrastiivisessa analyysikerroksessa soveltaen käyttöön
    TDT-jäsentimen periaatteen jäsentää sivulauseita. Tämä on lähempänä
    perinteistä dependenssiteorian näkemystä (Siewierska 1988: 176) ja
    toisaalta on hyödyksi tietää, että verbi, josta esimerkiksi ajanilmaukset
    riippuvat, on juuri sivulauseen pääverbi. SN-jäsennystä muutetaan siten,
    että sivulauseen pääverbistä tehdään päälauseen dependentti, josta
    sivulauseen aloittava konjunktio riippuu.

    Kontrastiivinen analyysikerros toteutetaan siten, että kaikki alisteisen
    sivulauseen pääsanat luokitellaan cdep-kategoriaan, jolloin niistä käy ilmi,
    että kyseessä on sivulauseen muodostama täydennys tai määrite, muttei sitä,
    minkä tyypin argumentti on kyseessä. Kuvatunlainen kompromissi on väistämätön,
    sillä TDT-analyysi ei anna sivulauseiden suhteesta pääsanaansa yhtä tarkkaa
    informaatiota kuin SN-analyysi ja toisaalta SN-analyysi ei jaottele
    sivulauseita sen mukaan, ovatko ne täydennyksiä vai määritteitä. Tuloksena on
    väljempi yläkäsite, josta käy ilmi se, että kyseessä on sivulauseen muodostama
    argumentti. Tarkempi informaatio ei sinänsä katoa, sillä se on edelleen läsnä
    kielikohtaisissa jäsennyksissä.
    """
    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the cdep category in TDT')
    updater.search = makeSearch(database=dbcon.dbname, dbtable = 'fi_conll', ConditionColumns={'deprel':('advcl','ccomp')})
    updater.simpleupdate(deprel='cdep')

def adpos(dbcon=False):
    """
    Kuten esimerkeistä @parsers1fi--@parsers1ru havaittiin, TDT- ja SN-jäsentimet
    eroavat lähtökohtaisesti siinä, miten adpositiorakenteiden pääsana
    määritellään. Kontrastiivinen jäsennys seuraa tältä osin SN-jäsennyksen
    jäsennystapaa, niin että TDT-tapauksissa riippuvuussuunta käännetään.
    Adpositioluokan nimi on kuitenkin TDT-analyysin mukaisesti *adpos*.
    SN-analyysissa prepositiot analysoidaan omalla luokallaan *предл*. Ongelmia
    aiheuttaa kuitenkin se, että SN-analysoitu aineisto sisältää myös
    adpositiorakenteita, jotka on analysoitu квазиагент-luokkaan.
    """

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the adpos category in TDT')
    #Käännä riippuvuus ja tee entisestä pääsanasta adpos
    updater.search = makeSearch(database=dbcon.dbname,dbtable='fi_conll',  ConditionColumns={'deprel':('adpos',)})
    updater.Update(updateType='DependentBecomesHead',matchdep='head',headdep='adpos')

def attr(dbcon=False):
    """Kaikkiin kielen tilanteisiin tarkoitettujen jäsenninten on luonnollisesti pyrittävä mahdollisimman
    suureen tarkkuuteen myös alemman tason dependenssisuhteissa. Tämän vuoksi erilaisia substantiivia tai
    adjektiivia määrittäviä sanoja kuvataan melko monilla alaluokilla. Näitä ovat TDT-jäsennyksessä muun
    muassa luokat amod, det ja quantmod. SN-jäsennyksessä vastaavan tason kategorioita ovat esimerkiksi
    opred, appos, ja utotšn.

    Tämän tutkimuksen kannalta näillä suhteilla ei useinkaan ole suurta merkitystä, sillä oleellista on
    erotella elementtejä, joiden suhteen ajanilmausten sijaintia olisi mielekästä määrittää. Tämän vuoksi
    kontrastiiviseen analyysikerrokseen muodostuu erittäin suuri alempien dependenssitasojen luokka, jota
    merkitään nimityksellä attr."""

    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'create the attr category in TDT')
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('amod','det','quantmod','poss')})
    updater.simpleupdate(deprel='attr')

def conj(dbcon=False):
    """
    TDT-jäsennyksessä rinnasteiset elementit merkitään conj-, parataxis- ja cc-kategorioihin.

    Toisin kuin SN-jäsennin, TDT-jäsennin katsoo niin rinnastuskonjunktion (joka
    luokitellaan kategoriaan cc) kuin myöhemmät rinnastettavat elementitkin (conj)
    ensimmäisen rinnastettavan elementin dependenteiksi

    Kontrastiivisessa analyysissa lähdetään TDT-jäsennyksen mukaisesta
    perusajatuksesta siinä, että rinnastetun lauseen pääsana tai myöhempi
    rinnastettu elementti katsotaan ensimmäisen rinnastettavan elementin (eikä
    rinnastuskonjunktion) dependentiksi. Rinnastuskonjunktiot merkitään TDT:n
    tapaan cc-kategorialla, ja kaikki rinnastettavat elementit analysoidaan
    conj-kategoriaan kuuluviksi.

    On vielä huomattava, että SN-jäsennyksessä sotšin-tyyppiä käytetään
    rinnastuskonjunktioiden lisäksi luettelomuotoisissa rinnastustapauksissa myös
    luettelon osien kategorisointiin -- TDT-analyysi luokittelee vastaavat
    tilanteet osaksi conj-kategoriaan, osaksi erilliseen parataxis-kategoriaansa.
    Tässä suhteessa kontrastiivista analyysia yksinkertaistetaan niin, että TDT:n
    parataxis-elementit samoin kuin ne venäjän sotšin-tapaukset, jotka eivät ole
    rinnastuskonjunktioita, luokitellaan conj-kategoriaan.

    """
    updater = deptypetools.DepTypeUpdater(dbcon, 'fi_conll', 'Create the conj category in TDT')
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('conj','parataxis')})
    updater.simpleupdate(deprel='conj')
    LogNewDeprel('Create the cc category in TDT')
    updater.search = makeSearch(database=dbcon.dbname, dbtable='fi_conll', ConditionColumns={'deprel':('cc',)})
    updater.simpleupdate(deprel='cc')

def fixChains(dbcon=False):
    """Lopuksi saattaa olla tarve korjata joitakin vääriä
    contr_deprel-merkintöjä, esim. apuverbiketjujen tuloksena syntyneita
    aux-tapauksia
    """

    LogNewDeprel('Fix auxes to infcomp')
    dbcon.query('UPDATE fi_conll SET contr_deprel = %(contrdep)s WHERE  contr_deprel IN %(oldcontrdep)s',{'contrdep':'infcomp','oldcontrdep':('aux','auxpass','neg')})
    log('to be updated: {} database rows.'.format(dbcon.cur.rowcount))
