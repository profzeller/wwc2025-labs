FROM python:3.11-slim

WORKDIR /app

COPY hub/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Hub application code
COPY hub/app ./app

# Bake the lab registry into the hub image (no host bind-mounts for config)
COPY labs/labs.json ./labs/labs.json

ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

CMD ["python", "-c", "from app import create_app; app=create_app(); app.run(host='0.0.0.0', port=5000)"]
