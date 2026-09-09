#!/bin/sh
set -eu

nginx_resolver=$(awk '/^nameserver / { print $2; exit }' /etc/resolv.conf)
case "$nginx_resolver" in
    *:*) nginx_resolver="[$nginx_resolver]" ;;
esac
export NGINX_RESOLVER="$nginx_resolver"

envsubst '${PORT} ${SIFT_OS_API_ORIGIN} ${NGINX_RESOLVER}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
