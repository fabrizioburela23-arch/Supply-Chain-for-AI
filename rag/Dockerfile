# Khipu Finance — RAG (Second Brain) microservice
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV RAG_PORT=5051
ENV CHROMA_PATH=/data/chroma
EXPOSE 5051

CMD ["gunicorn", "--bind", "0.0.0.0:5051", "--workers", "2", "--timeout", "120", "rag_server:app_rag"]
