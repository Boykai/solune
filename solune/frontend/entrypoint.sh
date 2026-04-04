#!/bin/sh
# Entrypoint for the frontend nginx container.
# Substitutes BACKEND_ORIGIN into the nginx config template at startup.
# Default: http://backend:8000 (docker-compose internal DNS).
export BACKEND_ORIGIN="${BACKEND_ORIGIN:-http://backend:8000}"

# Validate BACKEND_ORIGIN is a well-formed http(s) URL
case "$BACKEND_ORIGIN" in
  http://*|https://*)
    ;;
  *)
    echo "ERROR: BACKEND_ORIGIN must start with http:// or https://" >&2
    exit 1
    ;;
esac

envsubst '${BACKEND_ORIGIN}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
