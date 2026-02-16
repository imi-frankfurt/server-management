# Dockerfile
FROM python:3.14

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["fastapi", "run", "app.py", "--port", "80"]