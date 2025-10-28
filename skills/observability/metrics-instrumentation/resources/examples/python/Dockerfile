FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY flask_metrics.py .

# Expose metrics port
EXPOSE 8080

# Run application
CMD ["python", "flask_metrics.py"]
