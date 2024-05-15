# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /dashboard
WORKDIR /dashboard

# Copy the current directory contents into the container at /dashboard
COPY . /dashboard

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8083

# Define environment variable
# ENV NAME World

# Run catalogManager.py when the container launches
CMD ["python", "webDashboard.py"]