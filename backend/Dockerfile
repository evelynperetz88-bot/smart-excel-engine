# Smart Excel Engine — production Docker image
# Built for Render.com Web Service (also works on Fly, Railway, Cloud Run, ECS).
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies:
#   - ghostscript: real PDF/A post-processing
#   - fonts-dejavu, fonts-noto-core: Hebrew/Latin glyphs
#   - fontconfig: required by reportlab to find fonts
#   - libxml2/libxslt: openpyxl/python-docx
#   - tini: proper PID-1 signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
        ghostscript \
        fonts-dejavu \
        fonts-noto-core \
        fontconfig \
        tini \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Persistent storage path — points at /var/data when a Render disk is mounted,
# otherwise falls back to /tmp/sxe-storage (ephemeral but functional).
ENV STORAGE_DIR=/var/data \
    PORT=10000 \
    CORS_ORIGINS=*

EXPOSE 10000

# Use tini for proper signal forwarding to uvicorn
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "mkdir -p \"$STORAGE_DIR\" && uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
