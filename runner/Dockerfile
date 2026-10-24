FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TMPDIR=/work

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY sandbox_runner.py /runner.py

# 与 docker run --user 65534:65534 保持一致，容器内不使用 root
USER 65534:65534

ENTRYPOINT ["python3", "-u", "/runner.py"]
