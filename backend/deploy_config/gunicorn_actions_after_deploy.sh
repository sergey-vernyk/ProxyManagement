#!/bin/bash

supervisor_program_name=$1


if [[ -z "$supervisor_program_name" ]]; then
    echo "Usage: gunicorn_actions_after_deploy <supervisor_programm_name>"
    exit 1
fi

program_status=$(sudo supervisorctl status "$supervisor_program_name") 

if [[ "$program_status" == *"ERROR"* ]]; then
	error_message=$(echo "$program_status" | grep -oP '\(.*?\)')
    echo "Error: $error_message"
	exit 1
fi

if sudo supervisorctl status "$supervisor_program_name" | grep -q 'RUNNING'; then
    sudo supervisorctl stop "$supervisor_program_name"
    echo "Restarting NGINX"
    sudo nginx -s reload
    echo -e "Start gunicorn server from supervisor program '$supervisor_program_name'"
    sudo supervisorctl start "$supervisor_program_name"
else
    echo "Restarting NGINX"
    sudo nginx -s reload
    echo -e "Start gunicorn server from supervisor program '$supervisor_program_name'"
    sudo supervisorctl start "$supervisor_program_name"
fi;


