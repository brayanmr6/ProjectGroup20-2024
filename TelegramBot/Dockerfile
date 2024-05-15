# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /telegram_bot
WORKDIR /telegram_bot

# Copy the current directory contents into the container at /telegram_bot
COPY . /telegram_bot

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8085 available to the world outside this container
EXPOSE 8085

# Run both chatbot.py when the container launches
CMD ["python", "chatbot.py"]