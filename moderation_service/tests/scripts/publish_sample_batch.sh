#!/usr/bin/env sh
# Publie un lot d'exemple dans `contentQueue` (test manuel bout en bout).
# Pré-requis : Redis joignable, venv Python 3.12 activé.
set -eu

cd "$(dirname "$0")/../.."
exec python -m tests.scripts.publish_sample_batch "$@"
