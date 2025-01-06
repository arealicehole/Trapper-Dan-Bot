FROM python:3.12.7-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot script
COPY . .

# Run the bot
CMD ["python", "main.py"]
