package main

import "log"

// isQuiet and isSilent are set from flags in main() before any logging occurs.
var (
	isQuiet  bool
	isSilent bool
)

// logInfo logs progress and data output. Suppressed by -quiet and -silent.
func logInfo(format string, args ...any) {
	if !isQuiet && !isSilent {
		log.Printf(format, args...)
	}
}

// logError logs non-fatal errors. Suppressed by -silent only.
func logError(format string, args ...any) {
	if !isSilent {
		log.Printf(format, args...)
	}
}
