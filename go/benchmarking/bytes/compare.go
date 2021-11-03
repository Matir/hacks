package main

import (
	"fmt"
)

func main() {
	fmt.Println("vim-go")
}

func BytesEqualMasked(a, b, mask []byte) bool {
	if len(a) != len(b) || len(a) != len(mask) {
		return false
	}
	for i := 0; i < len(a); i++ {
		if (a[i] & mask[i]) != (b[i] & mask[i]) {
			return false
		}
	}
	return true
}
