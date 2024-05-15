# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /thingspeak_adaptor
WORKDIR /thingspeak_adaptor

# Copy the current directory contents into the container at /thingspeak_adaptor
COPY . /thingspeak_adaptor

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8087

# Define environment variable
# ENV NAME World

# Run catalogManager.py when the container launches
CMD ["python", "thingspeakAdaptor.py"]