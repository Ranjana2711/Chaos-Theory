FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

ENV HF_HOME=/home/user/.cache/huggingface \
    PORT=7860 \
    PYTHONUNBUFFERED=1

COPY --chown=user requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY --chown=user src/ ./src/
COPY --chown=user app.py ./
COPY --chown=user prompts/ ./prompts/
COPY --chown=user PROJECT_NOTES.md ./

EXPOSE 7860
CMD ["python", "app.py"]
