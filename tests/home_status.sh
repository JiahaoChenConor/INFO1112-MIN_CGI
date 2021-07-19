cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl -I 127.0.0.1:8070/ | diff - home_status_expected.out
kill $PID
