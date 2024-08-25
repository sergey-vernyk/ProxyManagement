#!/bin/bash

if [[ ! -e "/etc/nginx/sites-enabled/modem_proxy.conf" ]]; then
  cp modem_proxy.conf /etc/nginx/sites-enabled
fi
