#!/bin/bash

NAME=proxy_management
DIR=/home/sergey/PycharmProjects/AsyncSocketExchange/backend
USER=sergey
GROUP=sergey
WORKERS=3
WORKER_CLASS=uvicorn.workers.UvicornWorker
VENV=/home/sergey/.cache/pypoetry/virtualenvs/asyncsocketexchange-8pvtxjcX-py3.12/bin/activate
BIND=unix:$DIR/run/gunicorn.sock
LOG_LEVEL=error

cd $DIR
source $VENV

exec gunicorn main:app \
    --name $NAME \
    --workers $WORKERS \
    --worker-class $WORKER_CLASS \
    --user=$USER \
    --group=$GROUP \
    --bind=$BIND \
    --log-level=$LOG_LEVEL \
    --log-file=-
