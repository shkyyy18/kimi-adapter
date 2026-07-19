FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY kimi_adapter ./kimi_adapter

RUN pip install --no-cache-dir -e "."

EXPOSE 18231

CMD ["kimi-adapter", "--host", "0.0.0.0"]
