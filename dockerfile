# pakai python resmi
FROM python:3.11-slim

# kerja di /app
WORKDIR /app

# copy requirements dulu (biar cache-nya kepake)
COPY requirements.txt /app/requirements.txt

# install dependency
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy source code + PDF
COPY app.py /app/app.py
COPY Nafhan_Profile.pdf /app/Nafhan_Profile.pdf

# Railway biasanya kasih PORT env, kita expose 8080 aja defaultnya
EXPOSE 8080

# jalankan app
# kalau kamu mau pakai waitress:
CMD ["python", "app.py"]
