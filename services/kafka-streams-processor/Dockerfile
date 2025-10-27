FROM openjdk:17-jdk-slim

# Install Python for hybrid processing
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pom.xml .

# Download dependencies (if using Maven)
RUN apt-get update && apt-get install -y maven \
    && mvn dependency:go-offline || true \
    && apt-get remove -y maven \
    && apt-get autoremove -y

# Copy compiled JAR (if pre-built) - create empty if doesn't exist
RUN touch app.jar

# Health check script
COPY health_check.sh /health_check.sh
RUN chmod +x /health_check.sh

EXPOSE 8090

# JVM options for performance
ENV JAVA_OPTS="-Xms512m -Xmx2g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"

CMD ["java", "-jar", "app.jar"]