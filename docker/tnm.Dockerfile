FROM eclipse-temurin:17-jdk as builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src/tnm

# Copy TNM source (submodule)
COPY tnm /src/tnm

# Build shaded CLI jar
RUN chmod +x ./gradlew && ./gradlew :cli:shadowJar --no-daemon

FROM eclipse-temurin:17-jre

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built jar from builder stage
COPY --from=builder /src/tnm/cli/build/libs/shadow-all.jar /app/tnm-cli.jar

# No default CMD/ENTRYPOINT; we invoke the jar via docker-compose exec

