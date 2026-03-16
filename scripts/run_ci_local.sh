#!/usr/bin/env bash
set -euo pipefail

# Local CI helper: runs setup/lint/docs/build checks and intentionally skips
# unit-test execution. Use scripts/run_ci_docker_parallel.sh for unit tests.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_DIR="${CI_LOCAL_REPOS_DIR:-$HOME/repos}"
PYTHON_BIN="${PYTHON_BIN:-python}"

if [[ -n "${PIP_BIN:-}" ]]; then
    read -r -a PIP_CMD <<< "$PIP_BIN"
else
    PIP_CMD=("$PYTHON_BIN" "-m" "pip")
fi

RUN_DOCS=1
RUN_BUILD=1
SKIP_EXTERNAL_CLONES=0

usage() {
    cat <<'EOF'
Run bluesky-queueserver-api CI-style checks locally.

Usage:
  scripts/run_ci_local.sh [options]

Options:
  --no-docs                Skip docs build step.
  --no-build               Skip package build step.
  --skip-external-clones   Do not clone/install external repos (assume already installed).
  -h, --help               Show this help.

Environment overrides:
  PYTHON_BIN         Python executable (default: python)
  CI_LOCAL_REPOS_DIR Location for cloned repos (default: ~/repos)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-docs)
            RUN_DOCS=0
            ;;
        --no-build)
            RUN_BUILD=0
            ;;
        --skip-external-clones)
            SKIP_EXTERNAL_CLONES=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 2
            ;;
    esac
    shift
done

ensure_repo() {
    local repo_url="$1"
    local repo_name="$2"
    local repo_path="$REPOS_DIR/$repo_name"

    if [[ ! -d "$repo_path/.git" ]]; then
        git clone "$repo_url" "$repo_path"
    fi

    "${PIP_CMD[@]}" install "$repo_path"
}

echo "==> Using project root: $ROOT_DIR"
cd "$ROOT_DIR"

echo "==> Upgrade base packaging tools"
"${PIP_CMD[@]}" install --upgrade pip setuptools numpy

if [[ "$SKIP_EXTERNAL_CLONES" -eq 0 ]]; then
    echo "==> Install external dependencies from source"
    mkdir -p "$REPOS_DIR"
    ensure_repo "https://github.com/bluesky/bluesky-queueserver.git" "bluesky-queueserver"
    ensure_repo "https://github.com/bluesky/bluesky-httpserver.git" "bluesky-httpserver"
else
    echo "==> Skipping external clone/install step"
fi

echo "==> Install local package and dev dependencies"
"${PIP_CMD[@]}" install .
"${PIP_CMD[@]}" install -r requirements-dev.txt

echo "==> Run style checks"
pre-commit run --all-files
echo "==> Skipping unit tests (per local script configuration)"

if [[ "$RUN_DOCS" -eq 1 ]]; then
    echo "==> Build docs"
    make -C docs/ html
else
    echo "==> Skipping docs build"
fi

if [[ "$RUN_BUILD" -eq 1 ]]; then
    echo "==> Build distributions"
    $PYTHON_BIN setup.py sdist bdist_wheel
else
    echo "==> Skipping package build"
fi

echo "==> Local CI run completed successfully"
