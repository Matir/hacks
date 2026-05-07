# Build configuration
BINARY_NAME=asmsh
LOCAL_DIR=$(shell pwd)/third_party

# Detection logic
HAS_SYSTEM_KS=$(shell pkg-config --exists keystone && echo yes || echo no)
HAS_SYSTEM_CS=$(shell pkg-config --exists capstone && echo yes || echo no)

# Local paths
LOCAL_KS_PC=$(LOCAL_DIR)/keystone/lib/pkgconfig
LOCAL_CS_PC=$(LOCAL_DIR)/capstone/lib/pkgconfig

# Setup PKG_CONFIG_PATH
ifeq ($(HAS_SYSTEM_KS),no)
	ifneq ("$(wildcard $(LOCAL_KS_PC))","")
		export PKG_CONFIG_PATH := $(LOCAL_KS_PC):$(PKG_CONFIG_PATH)
		HAS_KS=yes
	else
		HAS_KS=no
	endif
else
	HAS_KS=yes
endif

ifeq ($(HAS_SYSTEM_CS),no)
	ifneq ("$(wildcard $(LOCAL_CS_PC))","")
		export PKG_CONFIG_PATH := $(LOCAL_CS_PC):$(PKG_CONFIG_PATH)
		HAS_CS=yes
	else
		HAS_CS=no
	endif
else
	HAS_CS=yes
endif

# Runtime paths for testing/running
export LD_LIBRARY_PATH := $(LOCAL_DIR)/keystone/lib:$(LOCAL_DIR)/capstone/lib:$(LD_LIBRARY_PATH)

.PHONY: all build test clean help deps-check

all: build

deps-check:
	@echo "Checking dependencies..."
	@echo "Keystone: $(HAS_KS) (System: $(HAS_SYSTEM_KS))"
	@echo "Capstone: $(HAS_CS) (System: $(HAS_SYSTEM_CS))"
	@if [ "$(HAS_KS)" = "no" ] || [ "$(HAS_CS)" = "no" ]; then \
		echo "Warning: Missing real dependencies. Build may fail or require -tags mock."; \
		echo "Run ./scripts/build_keystone.sh to install keystone locally."; \
	fi

build-keystone:
	@echo "Local Keystone not found. Building it now..."
	@./scripts/build_keystone.sh

build: deps-check
	@if [ "$(HAS_KS)" = "no" ]; then \
		$(MAKE) build-keystone; \
		$(MAKE) build; \
	elif [ "$(HAS_CS)" = "yes" ]; then \
		echo "Building with real engines..."; \
		go build -o $(BINARY_NAME) ./cmd/asmsh; \
	else \
		echo "Capstone missing. Building with MOCK engine (or install libcapstone-dev)..."; \
		go build -tags mock -o $(BINARY_NAME) ./cmd/asmsh; \
	fi

test:
	@if [ "$(HAS_KS)" = "yes" ] && [ "$(HAS_CS)" = "yes" ]; then \
		go test -v ./...; \
	else \
		echo "Missing real engines, running tests with -tags mock..."; \
		go test -tags mock -v ./...; \
	fi

clean:
	rm -f $(BINARY_NAME)
	rm -rf third_party/keystone-src/build

help:
	@echo "Available targets:"
	@echo "  make build      - Build the binary (auto-detects dependencies)"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Remove binary and build artifacts"
	@echo "  make deps-check - Check if Keystone/Capstone are available"
