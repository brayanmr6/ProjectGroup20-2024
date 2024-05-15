# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /telegram_chatbot2
WORKDIR /telegram_chatbot2

# Copy the current directory contents into the container at telegram_chatbot2
COPY . /telegram_chatbot2

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8084 available to the world outside this container
EXPOSE 8084

# Define environment variable
# ENV NAME World

# Run catalogManager.py when the container launches
CMD ["python", "chatbot2.py"]