# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy the entire project into the container
COPY . .

# Upgrade pip and install project dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose the port Flask/Gunicorn will run on
EXPOSE 5000

# Run the Flask app using gunicorn in production
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
