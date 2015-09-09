Valmistelu
==========

1. Tmx-tiedoston valmistelu jäsennystä(parseria) varten 
--------------------------------------------------------


* cd to corpora2/databasename -folder
* HUOM! Tätä ennen kannattaa varmistaa, että kielikoodit on kirjoitettu pienellä tmx:ssä

```
python3 ~/syntparsedmustikka/database_insertion/tmxtoparserimput.py <tmxfilename> <lang1> <lang2>...
```
Bulkkina:


2. Kopioi valmistellut tiedostot omiin kielikohtaisiin kansioihinsa
-------------------------------------------------------------------

```
mv tmx/*_fi.prepared fi_prepared_for_parser/
mv tmx/*_ru.prepared ru_prepared_for_parser/
```

Jäsennys
========

Venäjänkieliset
---------------

1. Mene SN-parserin kotikansioon:

```
cd /home/juho/asennus/rusparser
```

2. Poista vanhat jäsennettävät ja kopioi uudet tilalle

```
mv *prepared oldfiles/
cp ~/corpora2/syntparrus2/ru_prepared_for_parser/*prepared .
```

3. Varmista, että multimalt-skriptissä on oikea tiedostopolku.

4. Aja multimalt-skripti:

```
sh multimalt.sh
```

Yhden tiedoston jäsennyksen kesto vaihtelee n. 5 minuutista puoleen tuntiin.
Parseri varaa KAIKEN koneen muistin, joten mitään muuta ei pysty jäsennyksen
aikana tekemään.

Suomenkieliset
---------------

1. Mene TDT-parserin kotikansioon:

```
cd ~/Dropbox/VK/skriptit/python/finnish_dep_parser/Finnish-dep-parser/
```

2. Poista vanhat jäsennettävät ja kopioi uudet tilalle

```
mv *prepared oldfiles/
cp ~/corpora2/syntparrus2/fi_prepared_for_parser/*prepared .
```

3. Varmista, että multimalt-skriptissä on oikea tiedostopolku.

4. Aja multimalt-skripti:

```
sh multiparse.sh
```

Eli:

```
for file in *prepared
do 
    cat $file | ./parser_wrapper.sh > $file.conll
    cp  $file.conll  ~/corpora2/syntparrus2/fi_conll/
done
```

Yhden tiedoston jäsennyksen kesto vaihtelee n. 5 minuutista puoleen tuntiin.
Parseri varaa lähes kaiken  koneen muistin, joten välttämättä paljon muuta ei
pysty jäsennyksen aikana tekemään.

Syöttäminen tietokantaan
========================

1. Tietokannan luominen
-----------------------

ks.  /home/juho/syntparsedmustikka/database_insertion/database_structure.otl

2. Lähdekielen syöttäminen
--------------------------

```
cd ~/syntparsedmustikka/database_insertion/
python3 -i  insertconll_first_todb_bangs.py ~/corpora2/syntparrus2/ru_conll/pr_smertinemnogo.tmx_ru.prepared.conll 'syntparrus2' 'ru_conll'
```

3. Käännöskielten syöttäminen


Skripti kaiken tekemiseksi kerralla:
====================================

