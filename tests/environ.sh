cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl -H "Accept: GET" 127.0.0.1:8070/cgibin/environ.py | diff - environ_expected.out
kill $PID
