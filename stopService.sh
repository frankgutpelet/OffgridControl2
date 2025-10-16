pid=`ps -Af |grep OffgridControl2/main.py |grep -v grep |sed 's/\s\s*/ /g' |cut -d ' ' -f2`
cd web
./stopService.sh
kill $pid
