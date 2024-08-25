#!/bin/bash

domain=$1
server_port=$2

# Check if the correct number of arguments are provided
if [ "$#" -ne 2 ]; then
	echo "Usage: $0 <domain> <server_port>"
	exit 1
fi

# Export variables
export DOMAIN="$domain"
export SERVER_PORT="$server_port"

# Process the template and write the output to the Nginx configuration directory
envsubst '${DOMAIN} ${SERVER_PORT}' < modem_proxy.conf.template > /etc/nginx/conf.d/modem_proxy.conf

# Test Nginx configuration and reload if successful
if sudo nginx -t; then
	echo "Nginx configuration is valid. Reloading..."
	sudo nginx -s reload
else
	echo "Nginx configuration test failed. Please check the configuration."
	exit 1
