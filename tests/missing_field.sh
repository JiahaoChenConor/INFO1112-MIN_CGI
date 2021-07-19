cd ..
python3 webserv.py broken_cfg.cfg > temp.out
diff temp.out missing_field_expected.out



