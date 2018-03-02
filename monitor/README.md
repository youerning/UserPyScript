## User Manual.
- step 1: install the env of anaconda3.
- step 2: copy source code to somewhere you want(i copy all of this to /data/monitor).
- step 3: complete configuration of the monitor conf.
- step 4: edit crontab rule.
    > 30-55/5 9 * * 1-5 cd /data/monitor; /usr/local/anaconda3/bin/python monitor.py
    */5 10 * * 1-5 cd /data/monitor; /usr/local/anaconda3/bin/python monitor.py
    0-30/5 11 * * 1-5 cd /data/monitor; /usr/local/anaconda3/bin/python monitor.py
    */5 13 * * 1-5 cd /data/monitor; /usr/local/anaconda3/bin/python monitor.py
    */5 14 * * 1-5 cd /data/monitor; /usr/local/anaconda3/bin/python monitor.py
    */5 15 * * 1-5 cd /data/monitor; /usr/local/anaconda3/bin/python monitor.py
- step 5: waiting for notification
