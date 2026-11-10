# Development image for the frontend (Leptos, client-side rendered), served by Trunk on port 4200.
FROM rust:1.90-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends pkg-config libssl-dev ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Trunk 0.22 needs rustc >= 1.96; 0.21 is the latest compatible with this toolchain.
RUN rustup target add wasm32-unknown-unknown \
    && cargo install --locked trunk --version "~0.21"

WORKDIR /app

# Pre-fetch and pre-build dependencies to speed up the first `trunk serve`.
# The dummy crate's own artifacts are deleted afterwards: the real sources keep their
# (older) host mtimes, so otherwise cargo would consider the dummy binary up to date.
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs \
    && cargo build --target wasm32-unknown-unknown \
    && rm -rf src \
       target/wasm32-unknown-unknown/debug/.fingerprint/urban-tree-observatory-* \
       target/wasm32-unknown-unknown/debug/deps/urban_tree_observatory* \
       target/wasm32-unknown-unknown/debug/urban-tree-observatory*

COPY . .

EXPOSE 4200

CMD ["trunk", "serve", "--address", "0.0.0.0", "--port", "4200"]
