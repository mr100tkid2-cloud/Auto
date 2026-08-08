# Use official Python lightweight image
FROM python:3.9-slim

# Install Chromium and ChromeDriver
RUN apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirement files and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the files
COPY app.py .

# Command to run the Python script
CMD ["python", "-u", "app.py"]
