export PYTHONPATH=/home/frank/projects/OffGridControl/web/
ipaddress=`ifconfig wlan0 |grep netmask | sed 's/\s\s*/ /g' |cut -d ' ' -f3`
PYTHONPATH=$PYTHONPATH../;
python3 manage.py runserver $ipaddress:8000 > log/Django.log 2>&1&

