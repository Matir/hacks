package main

import "log"

// isQuiet, isSilent, and isVerbose are set from flags in main() before any logging occurs.
var (
	isQuiet   bool
	isSilent  bool
	isVerbose bool
)

// logInfo logs progress and data output. Suppressed by -quiet and -silent.
func logInfo(format string, args ...any) {
	if !isQuiet && !isSilent {
		log.Printf("[INFO] "+format, args...)
	}
}

// logError logs non-fatal errors. Suppressed by -silent only.
func logError(format string, args ...any) {
	if !isSilent {
		log.Printf("[ERROR] "+format, args...)
	}
}

// logDebug logs fine-grained debugging info. Enabled by -verbose, suppressed by -silent.
func logDebug(format string, args ...any) {
	if isVerbose && !isSilent {
		log.Printf("[DEBUG] "+format, args...)
	}
}
