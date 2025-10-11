FROM python:3.13-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY src/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code modules
COPY src/*.py .

# Copy email templates
COPY email-templates /email-templates

# Expose port for Functions Framework
EXPOSE 8080

# Set environment variable for Functions Framework
ENV FUNCTION_TARGET=budget_response_handler
ENV PYTHONUNBUFFERED=1
ENV TEMPLATE_DIR=/email-templates

# Run Functions Framework
CMD ["functions-framework", "--target=budget_response_handler", "--port=8080"]
