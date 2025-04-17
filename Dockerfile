# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set a working directory inside the container
WORKDIR /app

# Install system dependencies (like MongoDB client dependencies)
RUN apt-get update && apt-get install -y libmongoc-1.0-0 && rm -rf /var/lib/apt/lists/*

# Install pipenv (if you use pipenv) or use pip directly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files into the container
COPY . .

# Expose a dummy port to satisfy Render's requirement for an open port (if needed)
EXPOSE 10000

# Run the application
CMD ["python", "userbot.py"]