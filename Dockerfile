FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask requests

COPY src/node.py /app/node.py

RUN mkdir -p /logs

EXPOSE 8000

CMD ["python", "/app/node.py"]