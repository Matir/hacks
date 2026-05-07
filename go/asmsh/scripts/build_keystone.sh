#!/bin/bash

# Exit on error
set -e

# Get the repository root
REPO_ROOT=$(pwd)
INSTALL_DIR="${REPO_ROOT}/third_party/keystone"
SRC_DIR="${REPO_ROOT}/third_party/keystone-src"

echo "Building Keystone in ${INSTALL_DIR}..."

# Create third_party directory
mkdir -p "${REPO_ROOT}/third_party"

# Clone if not already present
if [ ! -d "${SRC_DIR}" ]; then
    echo "Cloning Keystone repository..."
    git clone https://github.com/keystone-engine/keystone.git "${SRC_DIR}"
else
    echo "Keystone source already exists, skipping clone."
fi

# Build and install
mkdir -p "${SRC_DIR}/build"
cd "${SRC_DIR}/build"

echo "Configuring with CMake..."
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX="${INSTALL_DIR}" \
      -DBUILD_SHARED_LIBS=ON \
      ..

echo "Building..."
make -j$(nproc)

echo "Installing..."
make install

echo ""
echo "Keystone built and installed successfully to ${INSTALL_DIR}"
echo ""
echo "To build asmsh using this library, use:"
echo "  export PKG_CONFIG_PATH=\"${INSTALL_DIR}/lib/pkgconfig:\$PKG_CONFIG_PATH\""
echo "  go build ./cmd/asmsh"
echo ""
echo "To run the binary, you may need:"
echo "  export LD_LIBRARY_PATH=\"${INSTALL_DIR}/lib:\$LD_LIBRARY_PATH\""
