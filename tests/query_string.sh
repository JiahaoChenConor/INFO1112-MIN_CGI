cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 1
curl localhost:8070/cgibin/query_string.py?name=jiahao | diff - query_string_expected.out
kill $PID
