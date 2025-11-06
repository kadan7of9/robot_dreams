# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY src /app

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

ENV MONGO_HOST=127.0.0.1
ENV MONGO_DB=crack_meter-db

# Run mqtt_mongo_bridge.py when the container launches
CMD ["python", "CSV_reader.py"]