FROM python:3.11-slim

RUN pip install --no-cache-dir flask

COPY app.py /app.py

EXPOSE 9091

CMD ["python", "/app.py"]
