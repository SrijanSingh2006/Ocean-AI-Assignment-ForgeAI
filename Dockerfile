FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FORGE_RUN_DIR=/data FORGE_REQUIRE_AUTH=1
WORKDIR /app
RUN groupadd -g 10001 forge && useradd -u 10001 -g forge -d /app -s /usr/sbin/nologin forge \
    && mkdir /data && chown 10001:10001 /data
COPY pyproject.toml ./
COPY forgeai ./forgeai
RUN python -m pip install --no-cache-dir .
COPY prompts ./prompts
COPY static ./static
COPY demos ./demos
COPY docs ./docs
COPY scripts ./scripts
COPY hosting ./hosting
COPY README.md launch.py package.json .gitignore .gitattributes ./
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/health', timeout=2).close()"]
CMD ["python", "-m", "forgeai", "serve", "--host", "0.0.0.0", "--port", "8000"]
