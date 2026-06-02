# Use a stable and slim Python base image
FROM python:3.10-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies for audio processing (ffmpeg and libsndfile are required by librosa/soundfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY server.py /app/

# Expose the default FastAPI port
EXPOSE 8000

# Start the server
CMD ["python", "server.py"]
