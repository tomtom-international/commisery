FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app
COPY . /app

RUN uv pip install -r requirements.txt

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
