FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ffmpeg git gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/maziggy/bambuddy.git . && \
    git checkout a9bb8ed8239602bf08a9914f85a09eeb2bf13d15

RUN pip install --no-cache-dir -r requirements.txt

COPY custom_main.py /app/custom_main.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9090

ENTRYPOINT ["/entrypoint.sh"]
