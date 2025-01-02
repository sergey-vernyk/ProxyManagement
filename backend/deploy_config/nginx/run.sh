#!/bin/sh

set -e

# Avoid replacing these with envsubst
export host=\$host
export request_uri=\$request_uri

envsubst '${DOMAIN} ${SERVER_PORT}' </etc/nginx/modem_proxy.conf.template >/etc/nginx/conf.d/modem_proxy.conf

nginx -g 'daemon off;'
