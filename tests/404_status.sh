cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl -I 127.0.0.1:8070/noFile.html 2> /dev/null | grep '404' | diff - 404_status_expected.out 
kill $PID
