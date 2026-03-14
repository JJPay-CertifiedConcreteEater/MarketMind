#!/bin/bash
while true
do
    git pull origin main
    python3 main.py
    echo "Bot crashed or restarted. Pulling and relaunching in 3 seconds..."
    sleep 3
done
