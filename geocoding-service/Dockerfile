FROM python:3.11-slim

WORKDIR /app

# Install dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY init_geonames.sh /init_geonames.sh
RUN chmod +x /init_geonames.sh

EXPOSE 8006

CMD ["/init_geonames.sh"]
