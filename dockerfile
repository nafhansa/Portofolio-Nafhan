# Gunakan base image Python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements dan install dependensi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file project (termasuk PDF)
COPY . .

# Ekspos port aplikasi (Railway akan set PORT runtime)
EXPOSE 8080

# Jalankan via waitress-serve, mengikuti PORT dari environment Railway
CMD ["/bin/sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-8080} app:app"]
