FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir flask==3.0.3

# Copy Flask app + baked-in data
COPY app ./app
COPY data ./data

EXPOSE 5000

# Optional: lightweight healthcheck (no curl dependency required)
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2).read()" || exit 1

CMD ["python", "/app/app/app.py"]
