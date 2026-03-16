#!/usr/bin/env bash
set -euo pipefail

SHARD_GROUP="${SHARD_GROUP:-1}"
SHARD_COUNT="${SHARD_COUNT:-3}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-/artifacts}"
PYTEST_EXTRA_ARGS="${PYTEST_EXTRA_ARGS:-}"
ALLOW_NO_TESTS="${ALLOW_NO_TESTS:-1}"

mkdir -p "$ARTIFACTS_DIR"

redis-server --save "" --appendonly no --daemonize yes

for _ in $(seq 1 50); do
    if redis-cli ping >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

if ! redis-cli ping >/dev/null 2>&1; then
    echo "Failed to start redis-server inside container" >&2
    exit 2
fi

export COVERAGE_FILE="$ARTIFACTS_DIR/.coverage.${SHARD_GROUP}"

pytest_cmd=(
    pytest
    --cov=./
    --cov-report=term-missing
    --cov-report=
    --junitxml="$ARTIFACTS_DIR/junit.${SHARD_GROUP}.xml"
    -vv
    --splits "$SHARD_COUNT"
    --group "$SHARD_GROUP"
)

if [[ -n "$PYTEST_EXTRA_ARGS" ]]; then
    pytest_cmd+=( $PYTEST_EXTRA_ARGS )
fi

set +e
"${pytest_cmd[@]}"
test_status=$?
set -e

if [[ "$test_status" -eq 5 && "$ALLOW_NO_TESTS" == "1" ]]; then
    echo "No tests collected for chunk ${SHARD_GROUP}/${SHARD_COUNT}; treating as success."
    test_status=0
fi

redis-cli shutdown nosave >/dev/null 2>&1 || true

exit $test_status
