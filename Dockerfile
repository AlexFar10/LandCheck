# Interim image: runs CI, then serves the current page on port 3000.
# Replace the app stage when FastAPI and React land. Keep the ci stage.

# Stage 1: CI. Its output appears in the Coolify build log.
FROM python:3.12-slim AS ci
WORKDIR /app
COPY pyproject.toml ./
COPY landcheck ./landcheck
COPY config ./config
COPY tests ./tests
RUN pip install --no-cache-dir -e ".[dev]" "ruff==0.8.4"
RUN set -e; \
    echo "===== CI: lint ====="; \
    ruff check --no-cache --select E9,F .; \
    echo "===== CI: tests ====="; \
    python -m pytest -q -p no:cacheprovider; \
    echo "===== CI: passed ====="; \
    touch /tmp/ci-passed

# Stage 2: app. Copying the marker forces Docker to run the ci stage first.
FROM python:3.12-slim AS app
WORKDIR /app
COPY --from=ci /tmp/ci-passed /tmp/ci-passed
COPY index.html ./index.html
RUN printf '{"status":"ok"}\n' > health \
    && useradd --create-home app \
    && chown -R app:app /app
USER app
ENV PORT=3000
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import os, urllib.request as r; r.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '3000') + '/health', timeout=2)"]
CMD ["sh", "-c", "exec python -m http.server \"$PORT\" --bind 0.0.0.0 --directory /app"]
