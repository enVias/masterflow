#!/bin/bash

# Railway-compatible init script for matchering-web
# Uses $PORT environment variable

file="./.secret_key"
if [ -f "$file" ]; then
    echo "Using an existing SECRET_KEY..."
else
    echo "Generating a new SECRET_KEY..."
    echo `date +%s|sha256sum|base64|head -c 50` > "$file"
fi

python3 manage.py makemigrations mgw_back
python3 manage.py migrate

# Use PORT from Railway, default to 8360
PORT=${PORT:-8360}
echo "Starting on port $PORT..."

# Create dynamic supervisord config
cat > /tmp/supervisord.conf << SUPERVISORD_EOF
[supervisord]
nodaemon=true
user=root

[program:redis]
command=redis-server
autorestart=true
stdout_logfile=/dev/null
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:mgcore]
directory=/app
command=python3 manage.py rqworker default
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true

[program:mgweb]
directory=/app
command=python3 manage.py runserver 0:$PORT
autorestart=true
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
redirect_stderr=true
SUPERVISORD_EOF

supervisord -c /tmp/supervisord.conf
