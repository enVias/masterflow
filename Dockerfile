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

# Copy our Railway-compatible init script
COPY init-railway.sh ./init-railway.sh
RUN chmod +x ./init-railway.sh

CMD ["./init-railway.sh"]
