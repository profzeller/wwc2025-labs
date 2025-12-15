FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir flask==3.0.3

# Copy Flask app
COPY app ./app

# Copy default lab data into the image
COPY data ./data

EXPOSE 5000

CMD ["python", "/app/app/app.py"]
