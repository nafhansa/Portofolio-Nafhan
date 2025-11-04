# image kecil aja
FROM python:3.13-slim

# bikin workdir
WORKDIR /app

# copy requirements dulu
COPY requirements.txt .

# install dep
RUN pip install --no-cache-dir -r requirements.txt

# copy semua source
COPY . .

# Railway bakal ngasih env PORT, kita pake itu
# jalankan pakai waitress (production grade)
CMD ["sh", "-c", "waitress-serve --listen=0.0.0.0:${PORT:-8080} app:app"]
