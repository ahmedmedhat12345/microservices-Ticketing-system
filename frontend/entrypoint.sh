#!/bin/sh
ENV=${ENV:-development}
TICKET_URL=${TICKET_URL:-http://localhost:5000}
SUPPORT_URL=${SUPPORT_URL:-http://localhost:5001}
REPORTING_URL=${REPORTING_URL:-http://localhost:5002}
NOTIFICATION_URL=${NOTIFICATION_URL:-http://localhost:5003}
sed -i "s|window.ENV = \"development\"|window.ENV = \"$ENV\"|g" /usr/share/nginx/html/index.html
sed -i "s|http://localhost:5000|$TICKET_URL|g" /usr/share/nginx/html/index.html
sed -i "s|http://localhost:5001|$SUPPORT_URL|g" /usr/share/nginx/html/index.html
sed -i "s|http://localhost:5002|$REPORTING_URL|g" /usr/share/nginx/html/index.html
sed -i "s|http://localhost:5003|$NOTIFICATION_URL|g" /usr/share/nginx/html/index.html
exec nginx -g "daemon off;"
