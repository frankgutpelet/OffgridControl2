pid=`ps -Af | grep 'python3 manage.py' | grep -v grep | awk '{print $2}'`
kill $pid
