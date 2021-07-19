cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 1
curl localhost:8070/cgibin/status_code.py | diff - status_code_expected.out
kill $PID
