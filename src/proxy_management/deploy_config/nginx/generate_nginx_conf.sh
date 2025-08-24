#!/bin/bash

domain=$1
server_port=$2

if [ "$#" -ne 2 ]; then
	echo "Usage: $0 <domain> <server_port>"
	exit 1
fi

export DOMAIN="$domain"
export SERVER_PORT="$server_port"

if [[ ! -d "/etc/nginx/includes" ]]; then
	sudo mkdir -p /etc/nginx/includes
fi

if envsubst '${DOMAIN} ${SERVER_PORT}' <modem_proxy.conf.template >/etc/nginx/conf.d/modem_proxy.conf; then
	echo "Processed modem_proxy.conf.template successfully."
else
	echo "Failed to process modem_proxy.conf.template. Please check the template file."
	exit 1
fi

if envsubst '${DOMAIN}' <./includes/ssl_settings.conf.template >/etc/nginx/includes/ssl_settings.conf; then
	echo "Processed ssl_settings.conf.template successfully."
else
	echo "Failed to process ssl_settings.conf.template. Please check the template file."
	exit 1
fi

# copy other necessary include files, excluding ssl_settings.conf.template
sudo find ./includes -type f ! -name 'ssl_settings.conf.template' -exec cp -v {} /etc/nginx/includes/ \;

if sudo nginx -t; then
	echo "Nginx configuration is valid. Reloading..."
	sudo nginx -s reload
else
	echo "Nginx configuration test failed. Please check the configuration."
	exit 1
fi
