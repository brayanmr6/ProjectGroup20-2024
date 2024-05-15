# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /data_analytics
WORKDIR /data_analytics

# Copy the current directory contents into the container at /data_analytics
COPY . /data_analytics

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8086

# Define environment variable
# ENV NAME World

# Run catalogManager.py when the container launches
CMD ["python", "dataAnalytics.py"]