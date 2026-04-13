FROM python:3.12-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 5000

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "client:app"]
