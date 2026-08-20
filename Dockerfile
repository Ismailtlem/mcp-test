FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py ./

ENV MCP_TRANSPORT=http

EXPOSE 8000

CMD ["uv", "run", "main.py"]
