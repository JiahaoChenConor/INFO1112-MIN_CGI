cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl -I localhost:8070/cgibin/noExist.py 2> /dev/null | diff - 500_status_expected.out 
kill $PID

