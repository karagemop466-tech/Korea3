#!/usr/bin/env bash
# fetch_data.sh — reproducibly re-download the raw data used by this project.
#
# Source: nflverse/nfldata (open, MIT/CC-licensed community dataset) on GitHub.
# We pin a commit SHA so that every number on the site can be reproduced byte-for-byte.
#
# Allowed-host note for sandboxed runners: this script intentionally fetches from
# codeload.github.com (a tarball of the pinned commit) instead of release-assets,
# because release assets redirect to a host that some sandboxes block.
set -euo pipefail

PIN_COMMIT="a270278f3ac4e937295fe6a27814b3c4a2b62645"   # nflverse/nfldata master, 2026-11-01T13:05:15Z
REPO="nflverse/nfldata"
DEST="$(cd "$(dirname "$0")/.." && pwd)/data/raw"

mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Fetching ${REPO} @ ${PIN_COMMIT}"
curl -sSfL --max-time 120 -o "$TMP/src.tar.gz" \
  "https://codeload.github.com/${REPO}/tar.gz/${PIN_COMMIT}"
tar -xzf "$TMP/src.tar.gz" -C "$TMP"
SRC="$TMP/nfldata-${PIN_COMMIT}/data"

for f in games.csv closing_lines.csv initial_lines.csv sc_lines.csv teams.csv; do
  cp "$SRC/$f" "$DEST/$f"
done

echo "Wrote to $DEST:"
( cd "$DEST" && sha256sum games.csv closing_lines.csv initial_lines.csv sc_lines.csv teams.csv )
