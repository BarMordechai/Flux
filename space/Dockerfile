# Hugging Face Space (Docker SDK): the Shetef processing server with the ivrit.ai Hebrew Whisper model.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH \
    FLUENCY_WHISPER_MODEL=ivrit-ai/whisper-large-v3-turbo-ct2 \
    HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt faster-whisper
# Bake the model into the image so a cold start does not download 1.6 GB.
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('ivrit-ai/whisper-large-v3-turbo-ct2', device='cpu', compute_type='int8')"

COPY --chown=user fluency fluency
COPY --chown=user web web
EXPOSE 7860
CMD ["uvicorn", "fluency.server:app", "--host", "0.0.0.0", "--port", "7860"]
