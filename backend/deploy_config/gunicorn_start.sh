#!/bin/bash

NAME=proxy-management
DIR=/home/ubuntu/code/Proxy_Management/AsyncSocketExchange/backend
USER=ubuntu
GROUP=ubuntu
WORKERS=2
WORKER_CLASS=uvicorn.workers.UvicornWorker
VENV=/home/ubuntu/.cache/pypoetry/virtualenvs/asyncsocketexchange-rDKi4hjE-py3.12/bin/activate
BIND=unix:$DIR/run/gunicorn.sock
LOG_LEVEL=error


echo "Changing directory to $DIR"
cd $DIR || { echo "Failed to change directory to $DIR"; exit 1; }

echo "Activating virtual environment"
source $VENV || { echo "Failed to activate virtual environment"; exit 1; }

echo "Ensuring run directory exists"
mkdir -p $DIR/run
chown $USER:$GROUP $DIR/run


exec gunicorn main:app \
    --name $NAME \
    --workers $WORKERS \
    --worker-class $WORKER_CLASS \
    --user=$USER \
    --group=$GROUP \
    --bind=$BIND \
    --log-level=$LOG_LEVEL \
    --access-logfile='/home/ubuntu/code/logs/gunicorn_access.log' \
    --log-file='/home/ubuntu/code/logs/gunicorn_error.log' \
    --forwarded-allow-ips='*'
