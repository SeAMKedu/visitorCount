#!/bin/bash
python3 yoloCount.py >> ./logs/yoloCount.log&
. venv38/bin/activate
python listener.py $1 >> ./logs/listener.log&
python emailing.py >> ./logs/emailing.log&
python parse_stats.py $1 $2 $3 >> ./logs/parse_stats.log&
python routes.py >> ./logs/routes.log&

sleep infinity
