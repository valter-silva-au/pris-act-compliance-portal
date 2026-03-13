# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy pyproject.toml to install dependencies
COPY pyproject.toml .

# Install dependencies from pyproject.toml
# Install build dependencies and the package
RUN pip install --no-cache-dir -e .

# Copy the source code
COPY src/ ./src/

# Expose port 8000 for the application
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
