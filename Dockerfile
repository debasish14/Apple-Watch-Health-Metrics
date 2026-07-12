# Backend image: pipeline + API. The frontend is built/hosted separately
# (S3+CloudFront or any static host).
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pipeline/ pipeline/
COPY api/ api/

# Pipeline artifacts live here; mount a volume in production so gold tables
# survive restarts (e.g. an EBS-backed volume on Elastic Beanstalk / EC2).
ENV HEALTH_DATA_DIR=/data
VOLUME ["/data"]

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "gunicorn -w 2 -b 0.0.0.0:${PORT} --timeout 300 api.app:app"]
