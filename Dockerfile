# Khipu Finance — main app
FROM python:3.11-slim

WORKDIR /app

# Versiones EXACTAS (constraints.txt): requirements.txt dice qué paquetes;
# constraints.txt fija con qué versión — un deploy ya no instala "lo último"
# por sorpresa (incidente SQLAlchemy 2.1, 2026-09-28).
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY . .

ENV PORT=8080 \
    PYTHONUNBUFFERED=1
EXPOSE 8080

# 1 worker + threads: el estado en memoria (SimpleCache, rate limits, bloqueo
# del PIN, agente de trading) vive UNA sola vez — con 2 workers divergía según
# quién atendía. NO subir --workers. Flask aquí es I/O-bound (proxy de APIs):
# los threads cubren la concurrencia (12; la IA va limitada aparte por
# AI_MAX_CONCURRENCY en core/ai.py y la base por el pool de ontology/db.py).
#
# `exec`: gunicorn pasa a ser el PID 1 y RECIBE el SIGTERM de Railway al
# redeployar → deja de aceptar peticiones y termina las que están en curso
# (--graceful-timeout 25, p. ej. una orden a Alpaca). Sin exec, `sh` se comía
# la señal y todo moría con el SIGKILL posterior. 25 s y NO 30: Railway manda el
# SIGKILL a los drainingSeconds (30, railway.toml); con el mismo valor una
# petición que termina justo en el límite competía con el SIGKILL. Si se cambia
# uno, mantener graceful-timeout ≤ drainingSeconds − 5.
#
# --max-requests queda APAGADO por defecto (0): con 1 solo worker, reciclarlo
# borra el estado en memoria (agente de trading en marcha, límites de tasa y
# el bloqueo del PIN — un atacante podría forzar el reciclaje para reiniciar
# el contador). Si algún día hay una fuga de memoria, se activa sin tocar
# código con GUNICORN_MAX_REQUESTS / GUNICORN_MAX_REQUESTS_JITTER en Railway.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads ${GUNICORN_THREADS:-12} --timeout 120 --graceful-timeout 25 --max-requests ${GUNICORN_MAX_REQUESTS:-0} --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-0} server:app"]
