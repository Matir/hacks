package main

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"os"
	"runtime"
	"runtime/pprof"
	"sync"
	"time"

	"golang.org/x/crypto/curve25519"
)

type pubKeyTest func([]byte) bool

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

func BytesEqualMaskedShort(a, b, mask []byte) bool {
	if len(a) < len(mask) || len(b) < len(mask) {
		return false
	}
	for i := 0; i < len(mask); i++ {
		if (a[i] & mask[i]) != (b[i] & mask[i]) {
			return false
		}
	}
	return true
}

func MakeMask(nbits int) []byte {
	l := nbits / 8
	if nbits%8 > 0 {
		l += 1
	}
	mask := make([]byte, l)
	for i := 0; i < nbits/8; i++ {
		mask[i] = byte(0xff)
	}
	if nbits%8 > 0 {
		mask[len(mask)-1] = 0xff ^ ((1 << (8 - (nbits % 8))) - 1)
	}
	fmt.Printf("Mask: %v\n", mask)
	return mask
}

func VanityToBytes(vanity string) ([]byte, []byte) {
	masklen := len(vanity) * 6
	// pad to multiple of 4
	if len(vanity)%4 != 0 {
		padLen := 4 - (len(vanity) % 4)
		for i := 0; i < padLen; i++ {
			vanity += "A"
		}
	}
	buf, err := base64.RawStdEncoding.DecodeString(vanity)
	if err != nil {
		panic(err)
	}
	mask := MakeMask(masklen)
	return buf[:len(mask)], mask
}

func MakeVanityTestFunction(vanity string) pubKeyTest {
	target, mask := VanityToBytes(vanity)
	return func(pubkey []byte) bool {
		return BytesEqualMaskedShort(target, pubkey, mask)
	}
}

// Returns the pubkey if this private key results in a usable pubkey, otherwise
// nil
func TestPrivateKey(privkey []byte, tfunc pubKeyTest) []byte {
	pubkey, err := curve25519.X25519(privkey, curve25519.Basepoint)
	if err != nil {
		fmt.Printf("Curve 25519 Error: %v", err)
		return nil
	}
	if tfunc(pubkey) {
		return pubkey
	}
	return nil
}

func FindKeyForTest(tfunc pubKeyTest) ([]byte, []byte) {
	buf := make([]byte, 32)
	for {
		if _, err := rand.Read(buf); err != nil {
			panic(err)
		}
		if pubkey := TestPrivateKey(buf, tfunc); pubkey != nil {
			return buf, pubkey
		}
	}
}

func PrintKeyPair(priv, pub []byte) {
	privstr := base64.StdEncoding.EncodeToString(priv)
	pubstr := base64.StdEncoding.EncodeToString(pub)
	fmt.Printf("%s %s\n", privstr, pubstr)
}

func FindAPair(vanity string) {
	testfunc := MakeVanityTestFunction(vanity)
	privkey, pubkey := FindKeyForTest(testfunc)
	PrintKeyPair(privkey, pubkey)
}

func BenchmarkKeyTest() {
	bmsec := 10
	tfunc := MakeVanityTestFunction("aaaa")
	ct := 0
	ncpu := runtime.NumCPU()
	fmt.Printf("Benchmarking on %d CPUs.\n", ncpu)
	wg := sync.WaitGroup{}
	wg.Add(ncpu)
	mu := sync.Mutex{}
	for i := 0; i < ncpu; i++ {
		go func() {
			lct := 0
			defer wg.Done()
			t := time.NewTimer(time.Duration(bmsec) * time.Second)
			tf := func(pkey []byte) bool {
				tfunc(pkey)
				select {
				case <-t.C:
					return true
				default:
					lct++
					return false
				}
			}
			FindKeyForTest(tf)
			mu.Lock()
			defer mu.Unlock()
			ct += lct
		}()
	}
	wg.Wait()
	fmt.Printf("%d keys/sec\n", ct/bmsec)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Printf("Usage: wgvanity <-profile|-bench|prefix>\n")
		return
	}
	if os.Args[1] == "-profile" {
		fp, _ := os.Create("wgvanity.prof")
		pprof.StartCPUProfile(fp)
		defer pprof.StopCPUProfile()
		BenchmarkKeyTest()
		return
	}
	if os.Args[1] == "-bench" {
		BenchmarkKeyTest()
		return
	}
	FindAPair(os.Args[1])
}
