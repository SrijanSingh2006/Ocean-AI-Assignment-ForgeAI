#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="${FORGE_RUNTIME_DIR:-$root/.runtime}"
version=b7525
model_file="$runtime/qwen2.5-0.5b-instruct-q4_k_m.gguf"
server="$runtime/llama-$version/llama-server"
checksum=74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db

if [[ "$(uname -s):$(uname -m)" != Linux:x86_64 ]]; then
  printf '%s\n' 'This downloader supports Linux x86_64. See README.md for Ollama and other systems.' >&2
  exit 2
fi
mkdir -p "$runtime"
if [[ ! -x "$server" ]]; then
  curl --fail --location --retry 2 \
    "https://github.com/ggml-org/llama.cpp/releases/download/$version/llama-$version-bin-ubuntu-x64.tar.gz" \
    -o "$runtime/llama-$version.tar.gz"
  tar -xzf "$runtime/llama-$version.tar.gz" -C "$runtime"
fi
if [[ ! -f "$model_file" ]]; then
  curl --fail --location --retry 2 \
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true" \
    -o "$model_file.part"
  printf '%s  %s\n' "$checksum" "$model_file.part" | sha256sum -c -
  mv "$model_file.part" "$model_file"
fi
exec "$server" -m "$model_file" -c 4096 -t "${FORGE_MODEL_THREADS:-2}" \
  --host 127.0.0.1 --port "${FORGE_MODEL_PORT:-8089}" --alias qwen2.5-0.5b --no-webui
