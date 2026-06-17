# LiteLLM proxy — routes OpenAI SDK calls to Claude
FROM ghcr.io/berriai/litellm:main-latest

COPY config.yaml /app/config.yaml

ENV PORT=8080

CMD ["sh", "-c", "litellm --config /app/config.yaml --port ${PORT}"]
