cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl localhost:8070/cgibin/cgi_test.py | diff - cgi_myTest_expected.out 
kill $PID
