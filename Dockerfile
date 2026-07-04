# Khipu Finance — main app
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# 1 worker + threads: el estado en memoria (SimpleCache, rate limits, agente
# de trading) vive UNA sola vez — con 2 workers divergía según quién atendía.
# Flask aquí es I/O-bound (proxy de APIs): los threads cubren la concurrencia.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 120 server:app"]
