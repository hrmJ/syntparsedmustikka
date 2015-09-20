#!/bin/bash

# Set these paths appropriately!
#This script is supposed to be run from its own directory

TMXFOLDER=/home/juho/corpora2/syntparfin2/tmx
#SNPARSER=/home/juho/corpora2/sn_parser/installation
SNPARSER= /home/juho/asennus/rusparser/
TDTPARSER=/home/juho/corpora2/Finnish-dep-parser/
RUPREPARED=/home/juho/corpora2/syntparfin2/ru_prepared_for_parser
FIPREPARED=/home/juho/corpora2/syntparfin2/fi_prepared_for_parser
FIPARSED=/home/juho/corpora2/syntparfin2/fi_conll
RUPARSED=/home/juho/corpora2/syntparfin2/ru_conll
PYTHONFOLDER=$(dirname $0)

mkdir -p $TMXFOLDER
mkdir -p $RUPREPARED
mkdir -p $FIPREPARED
mkdir -p $RUPARSED
mkdir -p $FIPARSED

#1. Prepare tmxes

#for tmxfile in $TMXFOLDER/*tmx
#do 
#    echo "Preparing $tmxfile..."
#    perl -pi -e 's/"(FI-FI|FI)"/"fi"/gi' $tmxfile
#    perl -pi -e 's/"(RU-RU|RU)"/"ru"/gi' $tmxfile
#    #python3 tmxtoparserimput.py $tmxfile ru fi
#    python3 tmxtoparserimput.py $tmxfile fi ru
#    echo "Prepared succesfully."
#done
#
###2.  Move  the prepared files:
#
#mv $TMXFOLDER/*_fi.prepared $FIPREPARED
#mv $TMXFOLDER/*_ru.prepared $RUPREPARED
#echo "Moved the prepared files to $FIPREPARED AND $RUPREPARED."
#echo "============================================================"

##3. Cd to the SNparser directory and start parsing:
#cd $SNPARSER
#mkdir -p oldfiles
#mv *prepared oldfiles/
#cp $RUPREPARED/*prepared .
#echo "Now starting to parse the Russian files, this probably takes long and consumes all available MEMORY!"
#echo "Be patient.."
#echo "**********************************************************************"
##3.3 Parse:
#for file in *prepared
#do 
#    sh russian-malt.sh $file
#    cp tmpmalttext.parse $RUPARSED/$file.conll
#done


echo "Now starting to parse the FINNISH files.... THIS consumes most of the CPU power"
#4. CD to TDT parsers directory and start parsing
cd $TDTPARSER
mkdir -p oldfiles
mv *prepared oldfiles/
cp $FIPREPARED/*prepared .
#4.1 parse
for file in *prepared
do 
    cat $file | ./parser_wrapper.sh > $file.conll
    mv  $file.conll  $FIPARSED/
done

echo "DONE!"
