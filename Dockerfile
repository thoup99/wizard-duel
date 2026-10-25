FROM node:22-alpine AS assets
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY scripts/build_frontend.mjs scripts/build_frontend.mjs
COPY frontend frontend
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SAMPLE_DIR=/app/samples
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && groupadd --gid 10001 mage \
    && useradd --uid 10001 --gid mage --no-create-home mage \
    && mkdir /app/samples && chown mage:mage /app/samples
COPY --chown=mage:mage backend backend
COPY --from=assets --chown=mage:mage /build/frontend frontend
USER mage
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"
# Rooms live in memory: do not increase the worker count or run multiple replicas.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-max-size", "65536"]
