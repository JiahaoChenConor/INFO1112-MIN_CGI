cd ..
python3 webserv.py config.cfg &
PID=$!
cd -
sleep 2
curl 127.0.0.1:8070/sample_html.html | diff - html_content_expected.out
kill $PID
