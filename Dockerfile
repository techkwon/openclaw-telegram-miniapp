FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MINIAPP_HOST=0.0.0.0 \
    MINIAPP_PORT=8765 \
    OPENCLAW_BASE_URL=http://host.docker.internal:18789 \
    MINIAPP_AUTH_DEBUG=false

EXPOSE 8765

CMD ["python", "bridge/openclaw_miniapp_bridge.py"]
