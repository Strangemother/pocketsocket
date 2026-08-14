#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

case "${1:-}" in
	"")
		pytest
		;;
	-c|--coverage)
		mkdir -p ../results/coverage/python
		pytest \
			--cov=pocketsocket \
			--cov-report=term-missing \
			--cov-report=html:../results/coverage/python
		;;
	*)
		printf 'Usage: %s [-c|--coverage]\n' "$0" >&2
		exit 2
		;;
esac