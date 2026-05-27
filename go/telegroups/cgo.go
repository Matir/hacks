package main

// Point CGO at the vendored TDLib headers and shared library.
// ${SRCDIR} expands to the absolute path of this source directory at build time.

// #cgo CFLAGS: -I${SRCDIR}/vendor/tdlib/include
// #cgo linux LDFLAGS: -L${SRCDIR}/vendor/tdlib/lib -Wl,-rpath,${SRCDIR}/vendor/tdlib/lib
import "C"
