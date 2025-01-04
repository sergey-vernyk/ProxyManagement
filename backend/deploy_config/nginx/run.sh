#!/bin/sh

set -e

# Avoid replacing these with envsubst
export host=\$host
export request_uri=\$request_uri

if [ ! -f "/etc/nginx/ssl-dhparams.pem" ]; then
    echo "dhparams.pem doesn't exist - creating it..."
    openssl dhparam -out /etc/nginx/ssl-dhparams.pem 2048
fi

envsubst '${DOMAIN} ${SERVER_PORT}' </etc/nginx/modem_proxy.conf.template >/etc/nginx/conf.d/modem_proxy.conf

nginx -g 'daemon off;'
