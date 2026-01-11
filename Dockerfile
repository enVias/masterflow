# Based on sergree/matchering-web
FROM python:3.10.9-slim

RUN apt update && apt -y install libsndfile1 ffmpeg redis-server supervisor

WORKDIR /app

# Clone the official matchering-web
RUN apt -y install git && \
    git clone https://github.com/sergree/matchering-web.git . && \
    apt -y remove git && \
    apt -y autoremove

RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x ./init.sh && mkdir -p data

# Create Railway-compatible init script inline (avoids COPY caching issues)
RUN echo '#!/bin/bash\n\
file="./.secret_key"\n\
if [ -f "$file" ]; then\n\
    echo "Using existing SECRET_KEY..."\n\
else\n\
    echo "Generating new SECRET_KEY..."\n\
    echo $(date +%s|sha256sum|base64|head -c 50) > "$file"\n\
fi\n\
python3 manage.py makemigrations mgw_back\n\
python3 manage.py migrate\n\
PORT=${PORT:-8360}\n\
echo "Starting on port $PORT..."\n\
redis-server --daemonize yes\n\
python3 manage.py rqworker default &\n\
python3 manage.py runserver 0.0.0.0:$PORT\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
