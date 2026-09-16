# Build context for this Dockerfile MUST be the repository root, not
# apps/api — that's what lets the COPY below reach the repo-level
# knowledge/ directory (a sibling of apps/api, not a child of it). Build
# with:  docker build -f apps/api/Dockerfile .   (run from the repo root)
# On Render: set "Dockerfile Path" to apps/api/Dockerfile and "Docker Build
# Context Directory" to the repo root (.) — see README for details.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ .

# The Pragati public/synthetic knowledge base (see app/knowledge/loader.py)
# lives at the repo root, not inside apps/api, since it's shared, non-code
# data rather than application source. Baked into the image here so
# production (Render, which has no bind-mount) has it — local dev via
# docker-compose additionally bind-mounts the same host directory over this
# path read-only, so edits there are picked up without a rebuild; this COPY
# is what makes a plain `docker run` of this image (no compose) work too.
COPY knowledge /knowledge
ENV KNOWLEDGE_DIR=/knowledge

RUN mkdir -p /app/app/data/uploads

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]