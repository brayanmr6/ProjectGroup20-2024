# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /device_connector
WORKDIR /device_connector

# Copy the current directory contents into the container at /device_connector
COPY . /device_connector

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8088 available to the world outside this container
EXPOSE 8088

# Define environment variable
# ENV NAME World

# Run catalogManager.py when the container launches
CMD ["python", "deviceConnector.py"]