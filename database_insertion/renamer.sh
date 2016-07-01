#!/bin/sh
name=`echo $1 | sed -e 's/\.[^.]*$//'`
newname="$name.txt.conll.metadata"
mv $1 $newname
