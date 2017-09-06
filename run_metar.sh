#!/bin/bash

METARDIR=/home/jgodwin/python/sfcplots
HOUR=`date +"%H" -u`
cd $METARDIR

rm metar.log

echo "Downloading METAR file (valid time: " $HOUR ")"
wget http://tgftp.nws.noaa.gov/data/observations/metar/cycles/$HOUR'Z'.TXT -O metar_data.txt
echo "Running Python script"
python sfcplots.py
echo "Shell script complete"
