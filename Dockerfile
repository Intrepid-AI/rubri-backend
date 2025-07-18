FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for SQLite database
RUN mkdir -p /app/data

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh && \
    # Fix line endings in case of Windows
    sed -i 's/\r$//' /app/startup.sh

# Expose port
EXPOSE 8000

# Start supervisor to run both FastAPI and Celery
CMD ["/app/startup.sh"]