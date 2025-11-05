FROM python:3.11-slim

WORKDIR /app

# install deps dulu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source + pdf
COPY . .

ENV PORT=8080

# run pakai waitress
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "app:app"]
