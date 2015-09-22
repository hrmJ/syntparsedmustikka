#! /usr/bin/env python
from deptypetools import LogNewDeprel, simpleupdate, makeSearch, log


class Featset:
    """Predefined feature sets and some methods to define them on the fly"""
    #REMEMBER  PRONONUNS
    def __init__(self):
        self.NounAcc =  self.createNounSet(cases = ('a',))
        self.NounDat =  self.createNounSet(cases = ('d',))
        self.PronAcc =  self.createPronSet(cases = ('a',))
        self.PronDat =  self.createPronSet(cases = ('d',))
        self.inf = ('Vmn----a-e','Vmn----a-p')
        #self.fin = ('Vmip3s-a-e')
        #Pronouns

    def ListDeprels(self):
        """List the original dependency relations of SN"""
        self.sndeps = list()
        with open("/home/juho/phdmanuscript/data/parrusdeprel.csv", 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                self.sndeps.append(row[0])


    def createNounSet(self,pos = 'N', nountypes = ('c','p'), genders = ('m','f','n'), numbers = ('s','p'), cases = ('n','g','a','i','d','l'), animacies = ('n','y')):
       """ Create tuples with all the specified feats"""
       items = self.additemlist([pos],nountypes)
       items = self.additemlist(items,genders)
       items = self.additemlist(items,numbers)
       items = self.additemlist(items,cases)
       items = self.additemlist(items,animacies)
       return tuple(items)

    def createPronSet(self,pos = 'P-', person = ('1','2','3','-'), genders = ('m','f','n','-'), numbers = ('s','p','-'), cases = ('n','g','a','i','d','l','-'), postype = ('n','a','r')):
       """ Create tuples with all the specified feats"""
        #P-3msin
       items = self.additemlist([pos],person)
       items = self.additemlist(items,genders)
       items = self.additemlist(items,numbers)
       items = self.additemlist(items,cases)
       items = self.additemlist(items,postype)
       return tuple(items)

    def additemlist(self, oldvalues, newvalues):
        """Create a list with all the combinations of the supplied values"""
        newitems = list()
        for oldvalue in oldvalues:
            for newvalue in newvalues:
                newitems.append(oldvalue + newvalue)
        return newitems

def gdep(dbcon=False):
    """"Aluksi määritellään kaikkien elementtien luokaksi gdep, jota sitten
    tarkennetaan niin pitkälle kuin mahdollista    """

    LogNewDeprel('Create the category of gdep in the SN data')
    dbcon.query('UPDATE ru_conll SET contr_head = head, contr_deprel = %(contrdep)s',{'contrdep':'gdep'})
    log('The gdep category was succesfully created')

def obj(dbcon=False):
    """" Toiseksi SN-analysoidun aineiston jäsennystä on tarkennettava niin, että
    siihenkin luodaan oma kategoriansa objekteille. 
    
    Teknisesti tämä ei ole erityisen
    vaikeaa, sillä objekteiksi voitaneen melko aukottomasti määrittää
    SN-analysoidusta aineistosta ne kompl1-luokkaan sijoitetut sanat, jotka a) ovat
    verbistä riippuvia nomineja ja b) on morfologisessa analyysissa luokiteltu joko
    akkusatiivisijaisiksi feminiineiksi/neutreiksi tai genetiivisijaisiksi
    elollisiksi maskuliineiksi/monikkomuodoiksi. 
    
    Luotavaan objektikategoriaan
    liitetään myös alkuperäisen SN-analyysin *dliteln*-luokka, joka sisältää
    akkusatiivissa käytettyjä keston ajanilmauksia.  Tämä ratkaisu on yhtenevä sen
    kanssa, miten TDT-analyysi käsittelee objektinsijaisia määrän adverbiaaleja
    (tarkemmin ks. ).
    """

    featset = Featset()
    LogNewDeprel('Create the category of object in the SN data')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable='ru_conll', ConditionColumns={'feat':featset.NounAcc,'deprel':('1-компл','2-компл','длительн')}, headcond = {'column':'pos','values':('V',)})
    simpleupdate(thisSearch, dbcon, deprel='obj',dbtable='ru_conll')

def nsubj(dbcon=False):
    """Nimetään uudelleen predik-kategoria nsubj:ksi"""

    LogNewDeprel('Create the category of nsubj in the SN data')
    dbcon.query('UPDATE ru_conll SET contr_deprel = %(contrdep)s WHERE deprel = %(deprel)s',{'contrdep':'nsubj','deprel':'предик'})
    log('Succesfully renamed predik to nsubj')

def nommod_own(dbcon=False):
    """"Create the category of nommod_own in SN
    NEEDS ADJUSTMENTS, Something's probably being left out 
    ------------------------------
    """
    featset = Featset()
    LogNewDeprel('Create the category of nommod_own in the SN data')
    thisSearch = makeSearch(database=dbcon.dbname,dbtable='ru_conll', ConditionColumns={'token':('у',),'deprel':('1-компл',)}, headcond = {'column':'lemma','values':('быть','есть', 'бывать', 'нет','мало','много')})
    simpleupdate(thisSearch, dbcon, deprel='nommod-own',dbtable='ru_conll')

def infcomp(dbcon=False):
    """Muokkaan kontrastiivista analyysikerrosta varten SN-analyysiä siten, että
    kaikki infinitiivit, jotka eivät ole lauseen pääsanan asemassa, 
    luokitellaan infcomp-kategoriaan
    (mukaanlukien verbillä ilmaistavat subjektit)

    Kuten nesessiivilauseiden osalta, tukeudun myös apuverbien kohdalla SN-analyysin mukaiseen malliin ja
    määrittelen kontrastiivisessa analyysikerroksessa pääsanaksi apuverbin ja dependentiksi pääverbin. Tästä
    seuraa, että apuverbin dependenssityyppi on joko ROOT tai jokin sivu- tai rinnasteisen lauseen pääsanan
    kategoria, jolloin pääverbille on erikseen määriteltävä oma kategoriansa – tällaiseksi soveltuu edellä
    SN-aineiston infinitiivisubjektien yhteydessä määritelty infcomp-luokka. TDT-analyysin kannalta tämä
    tarkottaa sitä, että kieltoverbien kantama informaatio lauseen kielteisyydestä katoaa kontrastiivisesta
    analyysikerroksesta. Myös TDT:n aux-, auxpass- ja SN:n analit-kategoriat poistuvat
    """

    featset = Featset()
    LogNewDeprel('Create the infcomp category in SN')
    thisSearch = makeSearch(database=dbcon.dbname,dbtable='ru_conll',  ConditionColumns={'deprel':('предик','1-компл','2-компл','аналит'),'pos':('V',),'feat':featset.inf})
    simpleupdate(thisSearch, dbcon, deprel='infcomp',dbtable='ru_conll')

def prtcl(dbcon=False):
    """
    SN-analyysissä kieltopartikkelit on
    luokiteltu kategoriaan ogranitš, johon kuuluvat myös käytännössä kaikki muut partikkelit konditionaalin
    12ilmaisevaa by-partikkelia lukuun ottamatta. Ogranitš-luokka siirretään sellaisenaan kontrastiiviseen
    analyysitasoon ja nimetään uudelleen tunnisteella prtcl. Tähän luokkaan yhdistetään myös alun
    perin analit-kategoriaan luokitellut by-partikkelit

    Partikkelit SN-datassa voivat olla:
    предик сент-предик 1-компл неакт-компл колич-огран сент-соч обст предл аппоз релят подч-союзн ROOT разъяснит опред эксплет вспом композ пролепт атриб оп-опред сравнит вводн соч-союзн кратн квазиагент аналит соотнос 2-компл ном-аппоз огранич сочин примыкат 3-компл присвяз сравн-союзн 
    """

    LogNewDeprel('Create the prtcl category in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'deprel':('огранич','аналит'), 'pos':('Q',)})
    simpleupdate(thisSearch, dbcon, deprel='prtcl',dbtable='ru_conll')

def semsubj(dbcon=False):
    """Otan käyttöön termin semsubj nesessiivilauseille ja muille vastaaville rakenteille, joissa SN-analyysi
    määrittää infinitiivimuotoisen verbin subjektiksi. Näin TDT:n nsubj ja SN:n
    2-kompl (1-kompl!) ja dat-subj muuttuvat (näiden lauseiden osalta) kontrastiivisessa
    kerroksessa muotoon semsubj.
    
    Rakenteen finiittimuotoinen verbi katsotaan
    SN-jäsennyksen mukaisesti juureksi ja infinitiivimuotoinen verbi luetaan infcomp-kategoriaan.
    
    Muutan kuitenkin SN-jäsennystä TDT-jäsennyksen mallin mukaiseksi siinä,
    että semsubj-kategorialla analysoitu sanamuoto katsotaan infinitiivimuodon
    eikä apuverbin dependentiksi. 
    
    HUOM!
    - verbi on joskus muu kuin predik (1-kompl,razjasnit)
    - semsubj-kandidaatti voi olla predik!
    - Lisäksi infinitiivitäydennys puuttuu joskus kokonaan (мне надо к нему)
    """

    LogNewDeprel('Create the class of SemSubj in SN ')
    featset = Featset()
    thisSearch = makeSearch(database=dbcon.dbname,dbtable='ru_conll',  ConditionColumns={'deprel':('1-компл', '2-компл','дат-субъект')})
    updated = 0
    #Check out whether there is a 'predik' or infinitival 1-kompl depending on the verbal head
    for key, matchlist in thisSearch.matches.items():
        for match in matchlist:
            match.matchedsentence.listDependents(match.matchedword.head)
            for codependent in match.matchedsentence.dependentlist:
                #If there is an infinitival codependent marked as predik or 1-kompl AND the nominal complement is in dative:
                if (codependent.deprel in ('предик','1-компл') and codependent.feat in featset.inf) and (match.matchedword.feat in featset.NounDat or match.matchedword.feat in featset.PronDat):
                    dbcon.query('UPDATE ru_conll SET contr_head = %(contrhead)s, contr_deprel = %(contrdep)s WHERE id = %(matchid)s',{'contrhead':codependent.tokenid,'contrdep':'semsubj','matchid':match.matchedword.dbid})
                    updated += 1
    log('Updated {} items in the db'.format(updated))

def prdctv(dbcon=False):
    """Koska ajanilmauksen sijainnin määrittelyn kannalta olisi hyödyllistä erottaa predikatiivit muista
    verbin täydennyksistä, pyrin kontrastiivisessa analyysitasossa tarkentamaan SN-jäsennyksen prisvjaz-
    kategoriaa. Tämä tapahtuu erottamalla omaksi prdctv-luokakseen sellaiset prisvjaz-kategorian sanat,
    jotka eivät ole prepositioita. Prepositioilla ilmaistavat prisvjaz-dependentit puolestaan liitetään edellä
    määriteltyyn nommod-kategoriaan."""

    LogNewDeprel('Create the prdctv category in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'deprel':('присвяз',), '!pos':('S',)})
    simpleupdate(thisSearch,dbcon,deprel='prdctv',dbtable='ru_conll')

def cdep(dbcon=False):
    """
    Sivulauseet SN-aineistossa:
    
    SN-jäsennystä muutetaan siten, että sivulauseen pääverbistä tehdään päälauseen dependentti,
    josta sivulauseen aloittava konjunktio riippuu.

    Kontrastiivinen analyysikerros toteutetaan siten, että kaikki alisteisen sivulauseen pääsanat luokitellaan
    cdep-kategoriaan, jolloin niistä käy ilmi, että kyseessä on sivulauseen muodostama täydennys tai määrite,
    muttei sitä, minkä tyypin argumentti on kyseessä. Kuvatunlainen kompromissi on väistämätön, sillä
    TDT-analyysi ei anna sivulauseiden suhteesta pääsanaansa yhtä tarkkaa informaatiota kuin SN-analyysi
    ja toisaalta SN-analyysi ei jaottele sivulauseita sen mukaan, ovatko ne täydennyksiä vai määritteitä.
    Tuloksena on väljempi yläkäsite, josta käy ilmi se, että kyseessä on sivulauseen muodostama argumentti.
    Tarkempi informaatio ei sinänsä katoa, sillä se on edelleen läsnä kielikohtaisissa jäsennyksissä.
    """

    LogNewDeprel('Create the cdep and the sc categories in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'deprel':('подч-союзн',)})
    updated = 0
    for key, matchlist in thisSearch.matches.items():
        for match in matchlist:
            try:
                mhead = match.matchedsentence.words[match.matchedword.head]
                dbcon.query('UPDATE ru_conll SET contr_head = %(contrhead)s, contr_deprel = %(contrdep)s WHERE id = %(matchid)s',{'contrhead':match.matchedword.tokenid,'contrdep':'sc','matchid':mhead.dbid})
                dbcon.query('UPDATE ru_conll SET contr_head = %(contrhead)s, contr_deprel = %(contrdep)s WHERE id = %(matchid)s',{'contrhead':mhead.head,'contrdep':'cdep','matchid':match.matchedword.dbid})
                updated += 1
            except KeyError:
                log('KeyError  with word {}, sentence {}'.format(match.matchedword.token,match.matchedsentence.sentence_id))
    log('Updated {} items in the db'.format(updated))

def conj(dbcon=False):
    """Rinnasteisten elementtien osalta SN-jäsennys käyttää kolmea eri luokkaa: sotš-sojuzn, sent-sotš ja
    sotšin.

    Kontrastiivisessa analyysissa lähdetään TDT-jäsennyksen mukaisesta perusajatuksesta siinä, että
    rinnastetun lauseen pääsana tai myöhempi rinnastettu elementti katsotaan ensimmäisen rinnastettavan
    elementin (eikä rinnastuskonjunktion) dependentiksi. 
    
    - Rinnastuskonjunktiot merkitään TDT:n tapaan cc-kategorialla, 
    - kaikki rinnastettavat elementit analysoidaan conj-kategoriaan kuuluviksi.

    On vielä huomattava, että SN-jäsennyksessä sotšin-tyyppiä käytetään rinnastuskonjunktioiden lisäksi
    luettelomuotoisissa rinnastustapauksissa myös luettelon osien kategorisointiin – TDT-analyysi luokittelee
    vastaavat tilanteet osaksi conj-kategoriaan, osaksi erilliseen parataxis-kategoriaansa. Tässä suhteessa
    kontrastiivista analyysia yksinkertaistetaan niin, että TDT:n parataxis-elementit samoin kuin ne venäjän
    sotšin-tapaukset, jotka eivät ole rinnastuskonjunktioita, luokitellaan conj-kategoriaan.

    MIKÄ on rinnastuskonjunktion pääsana?

    сент-соч pitää joskus erikseen, koska aina ei ole sotshin
    """

    LogNewDeprel('Create the conj and cc categories in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'deprel':('сочин','сент-соч','соч-союзн')})
    updated = 0
    for key, matchlist in thisSearch.matches.items():
        for match in matchlist:
            if match.matchedword.pos == 'C':
                #Update the conjunction
                dbcon.query('UPDATE ru_conll SET  contr_deprel = %(contrdep)s WHERE id = %(matchid)s',{'contrdep':'cc','matchid':match.matchedword.dbid})
            else:
                if match.matchedword.head == 0 or match.matchedword.head not in match.matchedsentence.words.keys():
                    pass
                else:
                    mhead = match.matchedsentence.words[match.matchedword.head]
                    while mhead.pos == 'C' and mhead.head in match.matchedsentence.words.keys():
                        mhead = match.matchedsentence.words[mhead.head]
                    #Update the actual coordinated element
                    dbcon.query('UPDATE ru_conll SET contr_head = %(contrhead)s, contr_deprel = %(contrdep)s WHERE id = %(matchid)s',{'contrhead':mhead.tokenid,'contrdep':'conj','matchid':match.matchedword.dbid})
                    updated += 1
    log('Updated {} items in the db'.format(updated))

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

    #kvaziagent pitää vielä miettiä!
    LogNewDeprel('create the attr category in sn')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable='ru_conll', ConditionColumns={'deprel':('опред', 'квазиагент', 'атриб', 'аппоз', 'разъяснит', 'количест', 'сравн-союзн', 'сравнит', 'вспом', 'соотнос', 'колич-вспом', 'электив', 'оп-опред', 'уточн', 'колич-огран', 'аппрокс-колич', 'кратн', 'нум-аппоз', 'эллипт', 'распред', 'композ')}, headcond = {'column':'pos','values':('a','n','p')})
    simpleupdate(thisSearch,dbcon,deprel='attr',dbtable='ru_conll')

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

    LogNewDeprel('Create the adpos category in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'deprel':('предл',)})
    simpleupdate(thisSearch, dbcon, deprel='adpos',dbtable='ru_conll')

def agent(dbcon=False):
    """
     """

    LogNewDeprel('Create the agent category in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'deprel':('агент',)})
    simpleupdate(thisSearch, dbcon, deprel='agent',dbtable='ru_conll')

def rel(dbcon=False):
    """
    Relatiivilauseiden tapauksessa SN-jäsennin ja TDT-jäsennin eroavat toisistaan
    poikkeuksellisen paljon. Syynä on TDT-jäsennyksen monikerroksisuus:
    TDT-analysoidussa aineistossa relatiivipronominit saavat ikään kuin kaksi
    dependenssianalyysia. Ensimmäisessä kerroksessa relatiivipronominit tulkitaan 
    relatiivilauseen sisäisesti, jolloin ne voidaan luokitella mihin tahansa
    kategoriaan, mikä niille lauseessa kuuluisi. Toisessa kerroksessa -- joka jää
    voimaan, kun aineisto on ajettu jäsentimen läpi -- relatiivipronominit
    analysoidaan *rel*-luokkaan kuuluviksi [@haverinen2013tdt, 30--31]. SN-jäsennin
    ei tee vastaavaa eroa, vaan käyttää suoraan niitä kategorioita, jotka
    TDT-jäsennyksessä kuuluvat ensimmäiseen, lopputuloksen ulkopuolelle jäävään
    kerrokseen.

    Analyysin kannalta SN-jäsentimen kaltainen yksikerroksinen lopputulos
    vaikuttaisi intuitiivisesti mielekkäämmältä: yksittäiset lauseet ovat
    vertailukelpoisempia, kun ei tehdä eroa sen suhteen, onko kyseessä
    relatiivilause, vai jokin muu lausetyyppi. Teknisesti on kuitenkin haastavaa
    muuttaa TDT:n rel-tyypiksi analysoituja elementtejä takaisin niiden ensimmäisen
    kerroksen mukaisiksi dependenssityypeiksi. Huomattavasti yksinkertaisempaa on
    muuttaa SN-analyysia: relatiivipronominien dependenssityyppi muutetaan
    muotoon *rel* riippumatta siitä, mikä se on alkuperäisen jäsennyksen mukaisesti.

    """

    LogNewDeprel('Create the rel category in SN')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable = 'ru_conll', ConditionColumns={'lemma':('который','чьей','' )})
    simpleupdate(thisSearch, dbcon, deprel='agent',dbtable='ru_conll')

def nommod(dbcon=False):
    """
    Kun muut luokat analysoitu, loput verbin täydennykset ja määritteet tähän luokkaan.
    
    TDT- ja SN-jäsennysten erilaiset periaatteelliset lähtökohdat näkyvät siinä, että SN-jäsennin luokittelee
    omaan obst-kategoriaansa elementit, jotka määrittävät verbiä tai muuta pääsanaa adverbiaalin tavoin.
    Näin esimerkiksi virkkeen 29 notšju saa luokakseen obst, mutta virkkeen 30 yönä tulee määritellyksi
    edelleen nommod-luokkaan.
    
    Ne prisvjaz-luokan elementit, jotka muodostetaan prepositioiden kautta, liitetään tähän.
    """

    featset = Featset()
    LogNewDeprel('Create the nommod category in sn')
    deprels = ('1-компл', '2-компл', '3-компл', '4-компл', '5-компл','обст','присвяз')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable='ru_conll', ConditionColumns={'deprel':deprels,'contr_deprel':('gdep',)})
    simpleupdate(thisSearch,dbcon,deprel='nommod',dbtable='ru_conll')

def advmod(dbcon=False):
    """ Muokkaan SN-jäsennyksen obst-kategoriaa ja
    TDT-jäsennyksen advmod-kategoriaa siten, että kontrastiiviseen jäsennykseen
    luodaan oma advmod-luokkansa. Tähän luokkaan rajataan SN-jäsennyksestä ne
    obst-kategorian sanat, joiden sanaluokka on adverbi (ja jotka
    automaattisesti ovat myös verbin dependenttejä) ja TDT-jäsennyksestä ne
    advmod-kategorian sanat, jotka ovat verbin dependenttejä.
    """

    LogNewDeprel('Create the advmod category in sn')
    thisSearch = makeSearch(database=dbcon.dbname, dbtable='ru_conll', ConditionColumns={'deprel':('обст',),'pos':('R',)}, headcond={'column':'pos','values': ('V',)})
    simpleupdate(thisSearch,dbcon,deprel='advmod',dbtable='ru_conll')

