FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

ENV FLASK_APP=app.py
ENV SECRET_KEY=change-me-in-production
ENV PROMETHEUS_URL=http://localhost:9090
ENV ALERTMANAGER_URL=http://localhost:9093

CMD ["python", "app.py"]