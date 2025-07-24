# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install the dependencies specified in the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Install git to clone repositories if needed
RUN apt-get update && apt-get install -y git 

RUN apt update && apt install -y curl pulseaudio-utils sox

# Copy the rest of the application code into the container at /app
COPY . . 

# Make start script executable
RUN chmod +x start.sh

# Expose the port for the fastapi 
EXPOSE 8000

# Expose the port for TCP
EXPOSE 9696

# Run both commands at startup
CMD ["bash", "start.sh"]

