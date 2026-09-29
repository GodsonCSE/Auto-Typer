# Universal Auto Typer — Docker image
#
# NOTE: A container has no access to a visitor's physical keyboard or
# desktop, so this image only ever serves the Browser mode of the app.
# Local System mode (native Windows keyboard input) requires running the
# app directly on a Windows machine via run.bat — it is not available in
# this container.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Hosting platforms (e.g. Render) provide PORT; default to 5000 for local
# `docker run` testing.
ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]
