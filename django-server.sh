#!/bin/bash
cd /home/odroid/gateway-latest-code/wh-project/
. venv/bin/activate
./manage.py runserver 0:8005
