#!/bin/bash
cargo build --release --bin rs-exporter
cross build --target x86_64-unknown-linux-gnu --release --bin rs-exporter