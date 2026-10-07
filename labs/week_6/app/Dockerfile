FROM python:3.13-slim
WORKDIR /app
COPY app.py docker_logger.py /app/
EXPOSE 8080
CMD ["python", "-u", "/app/app.py"]
