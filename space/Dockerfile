FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY space_app.py .
COPY app/ app/
COPY frontend/ frontend/
COPY docs/ docs/
COPY README.md .

EXPOSE 7860

CMD ["uvicorn", "space_app:app", "--host", "0.0.0.0", "--port", "7860"]
