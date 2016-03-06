#!/bin/bash

# Set these paths appropriately!
#This script is supposed to be run from its own directory

RUPARSED=/home/juho/corpora2/tbcorp/ru_parsed
RUMETA=/home/juho/corpora2/tbcorp/ru_metadata
FIPARSED=/home/juho/corpora2/tbcorp/fi_parsed
FIPARSED=/home/juho/corpora2/tbcorp/fi_metadata

#4.1 parse

for file in $RUPARSED/*conll
do 
    NAME=`basename $file .txt.prepared.conll`
    metafile="$NAME.metadata"
    echo $file
    python3 insert_crawled_blogpost.py $file $RUMETA/$metafile ru
done

echo "DONE!"


