package formatter

import (
	"fmt"
	"strings"
)

func FormatPretty(offset uint64, bytes []byte, asm string) string {
	var hexStr strings.Builder
	for _, b := range bytes {
		hexStr.WriteString(fmt.Sprintf("%02x ", b))
	}
	return fmt.Sprintf("0x%08x | %-20s | %s", offset, hexStr.String(), asm)
}

func FormatCArray(bytes []byte) string {
	var sb strings.Builder
	sb.WriteString("{ ")
	for i, b := range bytes {
		sb.WriteString(fmt.Sprintf("0x%02x", b))
		if i < len(bytes)-1 {
			sb.WriteString(", ")
		}
	}
	sb.WriteString(" }")
	return sb.String()
}

func FormatPythonArray(bytes []byte) string {
	var sb strings.Builder
	sb.WriteString("b\"")
	for _, b := range bytes {
		sb.WriteString(fmt.Sprintf("\\x%02x", b))
	}
	sb.WriteString("\"")
	return sb.String()
}

func Format(format string, offset uint64, bytes []byte, asm string) string {
	switch strings.ToLower(format) {
	case "c":
		return FormatCArray(bytes)
	case "python", "py":
		return FormatPythonArray(bytes)
	case "pretty":
		return FormatPretty(offset, bytes, asm)
	default:
		return FormatPretty(offset, bytes, asm)
	}
}
