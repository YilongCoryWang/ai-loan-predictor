FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Define environment variable
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Start the production server without auto-reload
CMD ["./start.sh"]