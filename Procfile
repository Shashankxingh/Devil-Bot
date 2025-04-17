# Use the official Python image as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files from the current directory to the container's working directory
COPY . .

# Set environment variables (if any, replace these with actual values in your environment)
# Example: Set the Telegram API ID, Hash, and Mongo URI in the Dockerfile (you can also use a .env file)
# ENV API_ID=<your_api_id>
# ENV API_HASH=<your_api_hash>
# ENV MONGO_URI=<your_mongo_uri>

# Run the userbot.py script when the container starts
CMD ["python", "userbot.py"]