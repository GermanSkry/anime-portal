#!/usr/bin/env bash
# Runs on the VPS, called by .github/workflows/deploy.yml over SSH.
# Lives at /opt/anime-portal/deploy.sh — `git pull` keeps it current.
#
# Pulls pre-built images instead of building here: the box has one vCPU and the
# backend image takes 15-40 minutes to build on it, starving everything else
# hosted on the same host.
set -euo pipefail

cd /opt/anime-portal

# Never `git stash -u` here. certs/, .env.production and start.sh are untracked,
# and -u sweeps them — which silently deletes the TLS certificate.
# A non-fast-forward must fail loudly rather than be papered over.
git pull --ff-only origin main

# The deploy key is restricted in authorized_keys with command="…/deploy.sh",
# which drops the client's environment, so the requested tag arrives in
# SSH_ORIGINAL_COMMAND instead. The character class keeps it to a tag.
if [ -z "${IMAGE_TAG:-}" ] && [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  IMAGE_TAG=$(printf '%s' "$SSH_ORIGINAL_COMMAND" | sed -n 's/.*IMAGE_TAG=\([A-Za-z0-9._-]*\).*/\1/p')
fi
export IMAGE_TAG="${IMAGE_TAG:-latest}"
echo "deploying ${IMAGE_TAG}"

docker compose pull python-backend go-search
docker compose up -d python-backend go-search

# the backend loads the embedding model at import, so `up -d` returns well
# before the API can actually answer
for i in $(seq 1 30); do
  if curl -sf --max-time 5 http://127.0.0.1:8010/health > /dev/null; then
    echo "api healthy after $((i * 5))s"
    break
  fi
  sleep 5
done
curl -sf --max-time 10 http://127.0.0.1:8010/health > /dev/null || {
  echo "api did not come back; recent logs:" >&2
  docker compose logs --tail 40 python-backend >&2
  exit 1
}
curl -sf --max-time 10 http://127.0.0.1:8011/health > /dev/null || {
  echo "go-search did not come back; recent logs:" >&2
  docker compose logs --tail 40 go-search >&2
  exit 1
}

# keep the disk from filling with superseded images
docker image prune -f --filter "until=168h" > /dev/null

echo "deployed ${IMAGE_TAG}"
