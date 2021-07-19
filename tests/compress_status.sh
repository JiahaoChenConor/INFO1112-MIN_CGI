cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 1
curl -I -H 'Accept-Encoding: gzip' 127.0.0.1:8070/sample_html.html 2> /dev/null | diff - compress_status_expected.out
kill $PID
