#!/usr/bin/env bash
# Wrapper that runs the `fep-sdd` CLI from a sibling clone.
#
# Expected layout:
#   ~/dev/fep-sdd/        ← CLI lives here
#   ~/dev/feptm/
#       └── feptm-workspace/scripts/sdd-cli.sh   ← this script
#
# To consume a different fep-sdd checkout, set FEP_SDD_DIR.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_FEP_SDD_DIR="$(cd "${SCRIPT_DIR}/../../../fep-sdd" 2>/dev/null && pwd || true)"
FEP_SDD_DIR="${FEP_SDD_DIR:-${DEFAULT_FEP_SDD_DIR}}"

if [[ -z "${FEP_SDD_DIR}" || ! -d "${FEP_SDD_DIR}" ]]; then
  echo "error: fep-sdd checkout not found." >&2
  echo "       expected at ${SCRIPT_DIR}/../../../fep-sdd or set FEP_SDD_DIR." >&2
  exit 2
fi

exec env -u VIRTUAL_ENV uv run --project "${FEP_SDD_DIR}" fep-sdd "$@"
