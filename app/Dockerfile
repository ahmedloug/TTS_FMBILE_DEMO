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


# Copy the rest of the application code into the container at /app
COPY . .

# Expose the port the app runs on
EXPOSE 8501


# Command to run the application
# CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]