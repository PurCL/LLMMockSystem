FROM 238280154298.dkr.ecr.us-east-1.amazonaws.com/python:3.11-slim

WORKDIR /app

# Install netcat for database connection checking
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Use entrypoint script to handle initialization and startup
ENTRYPOINT ["sh", "entrypoint.sh"]
