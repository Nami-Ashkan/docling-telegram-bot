#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-${SCRIPT_DIR}/.venv}"
PYTHON="${VENV_DIR}/bin/python3"
MAIN="${SCRIPT_DIR}/main.py"

if [[ ! -x "${PYTHON}" ]]; then
    printf 'Error: virtual-environment Python was not found at:\n  %s\n' "${PYTHON}" >&2
    printf 'Create it with:\n' >&2
    printf '  cd "%s"\n' "${SCRIPT_DIR}" >&2
    printf '  python3 -m venv .venv\n' >&2
    printf '  ./.venv/bin/python3 -m pip install --upgrade pip\n' >&2
    printf '  ./.venv/bin/python3 -m pip install docling "python-telegram-bot>=22,<23"\n' >&2
    exit 1
fi

if [[ ! -f "${MAIN}" ]]; then
    printf 'Error: main.py was not found at:\n  %s\n' "${MAIN}" >&2
    exit 1
fi

cd "${SCRIPT_DIR}"
exec "${PYTHON}" "${MAIN}" "$@"
