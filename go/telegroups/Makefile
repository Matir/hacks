TDLIB_REPO    := https://github.com/tdlib/td.git
TDLIB_DIR     := third_party/td
TDLIB_BUILD   := $(TDLIB_DIR)/build
VENDOR_TDLIB  := vendor/tdlib

GO      := go
# -mod=mod: vendor/ holds C libs only; Go deps live in the module cache.
GOFLAGS := -mod=mod

PWD := $(shell pwd)

CGO_CFLAGS  := -I$(PWD)/$(VENDOR_TDLIB)/include
CGO_LDFLAGS := -L$(PWD)/$(VENDOR_TDLIB)/lib -Wl,-rpath,$(PWD)/$(VENDOR_TDLIB)/lib

.PHONY: all build tdlib clean distclean

all: build

# ── TDLib ──────────────────────────────────────────────────────────────────────

$(TDLIB_DIR)/CMakeLists.txt:
	git clone --depth=1 $(TDLIB_REPO) $(TDLIB_DIR)

$(TDLIB_BUILD)/libtdjson.so: $(TDLIB_DIR)/CMakeLists.txt
	mkdir -p $(TDLIB_BUILD)
	cd $(TDLIB_BUILD) && cmake \
		-DCMAKE_BUILD_TYPE=Release \
		-DTD_ENABLE_LTO=OFF \
		-DCMAKE_INSTALL_PREFIX=$(PWD)/$(VENDOR_TDLIB) \
		..
	cd $(TDLIB_BUILD) && cmake --build . --target install -j$(shell nproc)

tdlib: $(TDLIB_BUILD)/libtdjson.so

# ── Go build ───────────────────────────────────────────────────────────────────

build: tdlib
	CGO_CFLAGS="$(CGO_CFLAGS)" \
	CGO_LDFLAGS="$(CGO_LDFLAGS)" \
	$(GO) build $(GOFLAGS) -o telegroups ./...

# ── Cleanup ────────────────────────────────────────────────────────────────────

clean:
	rm -f telegroups
	rm -rf $(TDLIB_BUILD) $(VENDOR_TDLIB)

distclean: clean
	rm -rf $(TDLIB_DIR)
