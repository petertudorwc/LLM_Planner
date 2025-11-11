FROM ollama/ollama:latest

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
RUN pip3 install --break-system-packages fastapi uvicorn pydantic httpx

# Copy application files
COPY src /app/src
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8001
EXPOSE 11434

# Override entrypoint to run our script
ENTRYPOINT []
CMD ["/bin/bash", "/start.sh"]
