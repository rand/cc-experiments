# BEFORE OPTIMIZATION
# Issues: Full base image, no multi-stage, runs as root, inefficient layers

FROM python:3.11
WORKDIR /app

# Inefficient: Installs everything in one go, large base image
COPY . .

# No cache optimization
RUN pip install -r requirements.txt

# Runs as root (security issue)
# No health check
# Shell form CMD (signal handling issue)
CMD python app.py

# Result: ~1.2GB image, slow builds, security issues
