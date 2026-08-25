FROM python:3.14.6-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY healthcare_migration.py .

CMD ["python", "healthcare_migration.py"]