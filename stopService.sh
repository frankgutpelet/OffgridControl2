pid=`ps -Af |grep OffgridControl2/main.py |grep -v grep |sed 's/\s\s*/ /g' |cut -d ' ' -f2`
kill $pid
#pid=`ps -Af |grep OffgridControl2/startHeizungssteuerung.py |grep -v grep |sed 's/\s\s*/ /g' |cut -d ' ' -f2`
#kill $pid
