#!/bin/bash

ssh_user=$1
ssh_host=$2
workdir=$3
repo_name=$4

if [[ $# -ne 4 ]]; then
    echo "Usage: ./start_staging_server.sh <ssh_user> <ssh_host> <workdir> <repo_name>"
    exit 1
fi

ssh "${ssh_user}@${ssh_host}" <<EOF
    cd "$workdir" || exit 1
    
    git remote set-url origin git@github.com:${repo_name}.git
    git checkout pre-deploy
    git pull origin pre-deploy
    
    cd ./backend
    /home/${ssh_user}/.local/bin/poetry install --no-interaction || exit 1
    VENV_PATH=\$(/home/${ssh_user}/.local/bin/poetry env info -p) || exit 1
    
    # check if server is already running and restart if needed
    if [[ -e "/tmp/stage_server_pid.txt" ]]; then
        echo "Server is already running. Restarting..."
        cat /tmp/stage_server_pid.txt | xargs kill -s TERM || echo "Warning: Failed to terminate existing server process"
        rm -f /tmp/stage_server_pid.txt
    fi

    # start the server with nohup and save PID
    nohup \$VENV_PATH/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --reload &> uvicorn_staging.log &
    echo \$! > /tmp/stage_server_pid.txt
    echo "Server started with PID: \$(cat /tmp/stage_server_pid.txt)"
EOF
