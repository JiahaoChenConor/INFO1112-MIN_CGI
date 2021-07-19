cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl 127.0.0.1:8070/ 2> /dev/null | diff - home_content_expected.out
kill $PID
