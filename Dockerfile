FROM python:3.10-slim

# Install system dependencies (ffmpeg, git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

# Command to run the Telegram bot
CMD ["python", "main.py"]
