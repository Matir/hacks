package repl

import (
	"encoding/hex"
	"fmt"
	"strings"
)

func StripComments(line string) string {
	commentMarkers := []string{"//", "#", ";"}
	for _, marker := range commentMarkers {
		if idx := strings.Index(line, marker); idx != -1 {
			line = line[:idx]
		}
	}
	return strings.TrimSpace(line)
}

func ParseHex(line string) ([]byte, error) {
	line = strings.ReplaceAll(line, " ", "")
	line = strings.ReplaceAll(line, ",", "")
	line = strings.ReplaceAll(line, "\\x", "")
	line = strings.ReplaceAll(line, "0x", "")
	
	if len(line)%2 != 0 {
		return nil, fmt.Errorf("hex string must have an even length")
	}
	
	return hex.DecodeString(line)
}
