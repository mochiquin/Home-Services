FROM eclipse-temurin:17-jre

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Use the prebuilt shaded CLI jar from the TNM submodule
COPY tnm/cli/build/libs/shadow-all.jar /app/tnm-cli.jar

# No default CMD/ENTRYPOINT; we invoke the jar via docker-compose exec

