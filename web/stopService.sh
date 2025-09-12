pid=`ps -Af |grep 'python3 manage.py' |grep -v grep |grep -v grep |sed 's/\s\s*/ /g' |cut -d ' ' -f 3`
kill $pid
