FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FORGE_RUN_DIR=/data
WORKDIR /app
RUN --mount=type=bind,target=/repository,readonly \
    --mount=type=secret,id=pip_ca,target=/run/secrets/pip_ca \
    groupadd -g 10001 forge \
    && useradd -u 10001 -g forge -d /app -s /usr/sbin/nologin forge \
    && mkdir /data \
    && cp -R /repository/forgeai /repository/prompts /repository/static /repository/demos /repository/docs \
      /repository/scripts /repository/tests /repository/pyproject.toml \
      /repository/README.md /repository/launch.py /repository/.gitignore \
      /repository/.gitattributes /repository/.env.example /repository/.dockerignore \
      /repository/Dockerfile /repository/render.yaml /app/ \
    && if [ -r /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi \
    && python -m pip install --no-cache-dir . \
    && chown -R 10001:10001 /app /data
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD ["python", "-c", "import os; from urllib.request import urlopen; urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health', timeout=2).close()"]
CMD ["sh", "-c", "export FORGE_REQUIRE_AUTH=1; exec python -m forgeai serve --host 0.0.0.0 --port \"${PORT:-8000}\""]
