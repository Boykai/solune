#!/bin/sh
# Entrypoint for the frontend nginx container.
# Substitutes BACKEND_ORIGIN into the nginx config template at startup.
# Default: http://backend:8000 (docker-compose internal DNS).
export BACKEND_ORIGIN="${BACKEND_ORIGIN:-http://backend:8000}"
envsubst '${BACKEND_ORIGIN}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
