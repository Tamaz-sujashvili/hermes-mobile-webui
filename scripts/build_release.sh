#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-v1.0.0}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="/tmp/hermes-mobile-webui-build"
PKG_NAME="hermes-mobile-webui-${VERSION}"
PKG_DIR="${BUILD_DIR}/${PKG_NAME}"

echo "==> Building Hermes Mobile WebUI ${VERSION}"

rm -rf "${BUILD_DIR}"
mkdir -p "${PKG_DIR}"

cd "${REPO_ROOT}"
git archive --format=tar HEAD | tar xf - -C "${PKG_DIR}"

echo "${VERSION}" > "${PKG_DIR}/VERSION"

cd "${BUILD_DIR}"
tar czf "/tmp/${PKG_NAME}.tar.gz" "${PKG_NAME}"

echo "==> Package created at /tmp/${PKG_NAME}.tar.gz"
echo ""
echo "To create GitHub release, run:"
echo "  gh release create ${VERSION} /tmp/${PKG_NAME}.tar.gz \\"
echo "    --title 'Hermes Mobile WebUI ${VERSION}' \\"
echo "    --notes 'Mobile WebUI for Hermes Agent with Tailscale support. See README for setup.'"
