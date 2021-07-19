cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 1
curl localhost:8070/cgibin/content_type_special.py | diff - content_type_special_expected.out
kill $PID
