# Stage 1: Build the Rust binary
FROM rust:1.78 as builder

# Set the working directory
WORKDIR /app

# Copy the Cargo.toml and Cargo.lock files
COPY Cargo.toml Cargo.lock ./

# Copy the source code
COPY src ./src

# Build the project in release mode
RUN cargo build --release

# Stage 2: Create the final image with the built binary
FROM debian:buster-slim

# Set the working directory
WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/target/release/rs-exporter ./energy-exporter

# Copy the dataset
COPY vm_data.csv ./vm_data.csv

# Expose the port
EXPOSE 9100

# Run the binary
CMD ["./energy-exporter"]