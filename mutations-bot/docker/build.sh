#!/usr/bin/env bash
set -euo pipefail

TAG="${1:?Usage: build.sh <tag>}"
IMAGE="cr.selcloud.ru/mutations-bot/mutations_bot:$TAG"

docker buildx build \
  --platform linux/amd64 \
  --load \
  -f docker/Dockerfile \
  -t "$IMAGE" \
  .

docker push "$IMAGE"
