#!/bin/bash

ssh_user=$1
ssh_host=$2
workdir=$3
repo_name=$4

ssh "${ssh_user}@${ssh_host}" <<EOF
    cd "$workdir" || exit 1
    
    git remote set-url origin git@github.com:${repo_name}.git
    git checkout pre-deploy
    git pull origin pre-deploy
    
    cd ./backend
    /home/${ssh_user}/.local/bin/poetry install --no-interaction || exit 1
    VENV_PATH=\$(/home/${ssh_user}/.local/bin/poetry env info -p) || exit 1
    
    if [[ ! -e "/tmp/stage_server_pid.txt" ]]; then 
        nohup \$VENV_PATH/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --reload &> uvicorn_staging.log &
        echo \$! > /tmp/stage_server_pid.txt
    else
        echo "Server is already running."
    fi
EOF
