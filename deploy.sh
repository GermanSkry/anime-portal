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

# The deploy workflow sets INGEST=1 when the data pipeline changed. Arrives via
# SSH_ORIGINAL_COMMAND for the same reason IMAGE_TAG does: the deploy key is
# pinned to this script, which drops the client environment.
if [ -z "${INGEST:-}" ] && [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  case "$SSH_ORIGINAL_COMMAND" in *INGEST=1*) INGEST=1 ;; esac
fi
if [ -z "${FETCH:-}" ] && [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  case "$SSH_ORIGINAL_COMMAND" in *FETCH=1*) FETCH=1 ;; esac
fi

if [ "${FETCH:-}" = "1" ]; then
  echo "refreshing the catalogue from AniList"
  # Runs inside the container just restarted above, so it uses the image that
  # was pulled, not whatever the host checkout happens to hold. The script
  # refuses to replace a good file with a smaller one, so a failed fetch leaves
  # the existing catalogue alone.
  docker compose exec -T python-backend python scripts/fetch_anime_enhanced.py
fi

if [ "${INGEST:-}" = "1" ]; then
  # `-s` is not enough: a failed fetch can leave the literal "[]", which is
  # 2 bytes. That is how this file was lost once already.
  if [ ! -f backend/data/anime.json ] || [ "$(wc -c < backend/data/anime.json)" -lt 1000 ]; then
    echo "INGEST requested but backend/data/anime.json is missing or empty." >&2
    echo "It is gitignored; fetch it first:" >&2
    echo "  docker compose exec python-backend python scripts/fetch_anime_enhanced.py" >&2
    exit 1
  fi
  echo "data pipeline changed, re-ingesting"
  # upserts on anilist_id and only re-embeds changed plots, so this is seconds
  # when the catalogue has not moved
  docker compose exec -T python-backend python scripts/ingest_anime.py
fi

# keep the disk from filling with superseded images
docker image prune -f --filter "until=168h" > /dev/null

echo "deployed ${IMAGE_TAG}"
