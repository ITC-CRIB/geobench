#!/bin/bash

# Hardcoded version of Node Exporter
NODE_EXPORTER_VERSION="1.8.0"  # Replace with the desired version

# Detect the operating system
OS=$(uname -s | tr '[:upper:]' '[:lower:]')

# Detect the architecture
ARCH=$(uname -m)

# Map architecture names to match Node Exporter naming convention
case "$ARCH" in
    "x86_64")
        ARCH="amd64"
        ;;
    "aarch64" | "arm64")
        ARCH="arm64"
        ;;
    "armv7l")
        ARCH="armv7"
        ;;
    *)
        echo "Unsupported architecture: $ARCH"
        exit 1
esac

# Construct the download URL
DOWNLOAD_URL="https://github.com/prometheus/node_exporter/releases/download/v$NODE_EXPORTER_VERSION/node_exporter-$NODE_EXPORTER_VERSION.$OS-$ARCH.tar.gz"

# Download the archive
echo "Downloading Node Exporter version $NODE_EXPORTER_VERSION for $OS-$ARCH from $DOWNLOAD_URL"
if command -v wget > /dev/null; then
    wget "$DOWNLOAD_URL"
elif command -v curl > /dev/null; then
    curl -LO "$DOWNLOAD_URL"
else
    echo "Neither wget nor curl is installed. Please install one of them and try again."
    exit 1
fi

# Extract the archive
ARCHIVE_NAME="node_exporter-$NODE_EXPORTER_VERSION.$OS-$ARCH.tar.gz"
tar -xzvf "$ARCHIVE_NAME"

# Move the node_exporter binary
mv "node_exporter-$NODE_EXPORTER_VERSION.$OS-$ARCH/node_exporter" ./

# Give execution right
chmod a+x ./node_exporter

# Remove the downloaded archive and extracted directory
rm -rf "$ARCHIVE_NAME" "node_exporter-$NODE_EXPORTER_VERSION.$OS-$ARCH"

echo "Node Exporter version $NODE_EXPORTER_VERSION installed successfully."