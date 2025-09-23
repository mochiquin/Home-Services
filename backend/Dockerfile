# Multi-stage build - Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Temurin JRE 11 (Adoptium)
RUN apt-get update && apt-get install -y curl ca-certificates && \
    curl -L -o /tmp/jre11.tar.gz \
      https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.24%2B8/OpenJDK11U-jre_x64_linux_hotspot_11.0.24_8.tar.gz && \
    mkdir -p /opt/java && tar -xzf /tmp/jre11.tar.gz -C /opt/java --strip-components=1 && \
    rm -rf /tmp/jre11.tar.gz /var/lib/apt/lists/*

# Java env (JRE 11)
ENV JAVA_HOME=/opt/java
ENV PATH="$JAVA_HOME/bin:$PATH"

# Create non-root user
RUN groupadd -r django && useradd -r -g django django

# Set working directory
WORKDIR /app

# Copy Python packages from build stage
COPY --from=builder /root/.local /home/django/.local

# Copy project files
COPY . .

# Set Python path
ENV PATH=/home/django/.local/bin:$PATH
ENV PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /home/django/.ssh && \
    ssh-keyscan github.com >> /home/django/.ssh/known_hosts && \
    chown -R django:django /app /home/django/.ssh && \
    chmod 700 /home/django/.ssh && \
    chmod 644 /home/django/.ssh/known_hosts

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# Start command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

