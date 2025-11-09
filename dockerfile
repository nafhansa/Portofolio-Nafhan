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

# Jalankan app.py (sudah pakai waitress di dalamnya dan membaca PORT)
CMD ["python", "-u", "app.py"]
