FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir broadlink paho-mqtt requests dotenv
COPY listener.py .
CMD ["python", "listener.py"]