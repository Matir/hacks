package main

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"flag"
	"fmt"
	"os"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"github.com/brk0v/directio"
	"golang.org/x/sys/unix"
)

const (
	BLOCK_SIZE      = uint64(4096)
	WORD_SIZE       = unsafe.Sizeof(uint64(0))
	MAX_ADDRS       = 10
	STATUS_INTERVAL = 1 * time.Second
)

type TestReport struct {
	// Blocks with an error on write
	failedWriteAddrs []uint64
	firstFailedWrite error
	// Blocks with an error on read
	failedReadAddrs []uint64
	firstFailedRead error
	// Blocks with incorrect read results
	wrongReadAddrs []uint64
}

type sizeStringer func(uint64) string
type statusCallback func(string, string, uint64, uint64, *TestReport)

func main() {
	noConfirmFlag := flag.Bool("dangerous-no-confirm", false, "Skip confirmation!")
	binaryFlag := flag.Bool("binary", false, "Use binary sizes.")

	flag.Parse()

	args := flag.CommandLine.Args()
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Device not specified!\n")
		flag.Usage()
		os.Exit(1)
	}
	devName := args[0]

	devSize, err := GetDeviceSize64(devName)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting device size: %s\n", err)
		os.Exit(1)
	}
	szToString := MakeSizeFunc(*binaryFlag)

	// Confirmation step
	if !*noConfirmFlag {
		fmt.Fprintf(os.Stderr, "Overwrite all data on %s (%s)? (yes in all caps) ", devName, szToString(devSize))
		os.Stderr.Sync()
		sc := bufio.NewScanner(os.Stdin)
		if !sc.Scan() {
			if err := sc.Err(); err != nil {
				fmt.Fprintf(os.Stderr, "Error reading input: %v\n", err)
			} else {
				fmt.Fprintln(os.Stderr, "Error reading input!")
			}
			os.Exit(1)
		}
		if strings.TrimSpace(sc.Text()) != "YES" {
			fmt.Fprintln(os.Stderr, "Confirmation not given, aborting!")
			os.Exit(1)
		}
	}

	rv := 0
	if res, err := PerformWriteReadTest(devName, devSize, szToString); err != nil {
		fmt.Fprintf(os.Stderr, "Error in performing test: %s\n", err)
		os.Exit(1)
	} else if res != nil {
		if res.firstFailedWrite != nil {
			fmt.Printf("First write error: %v\n", res.firstFailedWrite)
		}
		if res.firstFailedRead != nil {
			fmt.Printf("First read error: %v\n", res.firstFailedRead)
		}
		if res.failedWriteAddrs != nil && len(res.failedWriteAddrs) > 0 {
			fmt.Printf("%d write errors: %s\n", len(res.failedWriteAddrs), formatAddrList(res.failedWriteAddrs))
		}
		if res.failedReadAddrs != nil && len(res.failedReadAddrs) > 0 {
			fmt.Printf("%d read errors: %s\n", len(res.failedReadAddrs), formatAddrList(res.failedReadAddrs))
		}
		if rv == 0 {
			fmt.Printf("Test succeeded, %s okay\n", szToString(devSize))
		}
	} else {
		fmt.Fprintf(os.Stderr, "Error in test: no error, no report!\n")
		os.Exit(1)
	}
	os.Exit(rv)
}

func PerformWriteReadTest(name string, devSize uint64, szToString sizeStringer) (*TestReport, error) {
	statusFunc := makeStatusFunc(szToString)
	flags := os.O_RDWR | syscall.O_DIRECT | syscall.O_DSYNC | syscall.O_LARGEFILE | os.O_EXCL
	fp, err := os.OpenFile(name, flags, 0)
	if err != nil {
		return nil, fmt.Errorf("Error opening device %s: %w", name, err)
	}
	defer fp.Close()
	if verify, err := getDeviceSize64(fp); err != nil {
		return nil, fmt.Errorf("Error verifying size: %w", err)
	} else if verify != devSize {
		return nil, fmt.Errorf("Device %s size changed from %d (%s) to %d (%s)", name, devSize, szToString(devSize), verify, szToString(verify))
	}

	dio, err := directio.NewSize(fp, int(BLOCK_SIZE))
	if err != nil {
		return nil, fmt.Errorf("Error creating directio: %w", err)
	}

	var res TestReport

	// Start write portion
	for blockAddr := uint64(0); blockAddr < devSize; blockAddr += BLOCK_SIZE {
		statusFunc(name, "write", blockAddr, devSize, &res)
		if _, err := fp.Seek(int64(blockAddr), os.SEEK_SET); err != nil {
			res.failedWriteAddrs = append(res.failedWriteAddrs, blockAddr)
			if res.firstFailedWrite == nil {
				res.firstFailedWrite = fmt.Errorf("Error seeking to %#0x (%s): %w", blockAddr, szToString(blockAddr), err)
			}
			continue
		}
		blockData := makeBlock(blockAddr, BLOCK_SIZE)
		if n, err := dio.Write(blockData); err != nil {
			res.failedWriteAddrs = append(res.failedWriteAddrs, blockAddr)
			if res.firstFailedWrite == nil {
				res.firstFailedWrite = fmt.Errorf("Error writing to %#0x+%d (%s): %w", blockAddr, n, szToString(blockAddr), err)
			}
			continue
		}
		if err := dio.Flush(); err != nil {
			res.failedWriteAddrs = append(res.failedWriteAddrs, blockAddr)
			if res.firstFailedWrite == nil {
				res.firstFailedWrite = fmt.Errorf("Error flushing to %#0x (%s): %w", blockAddr, szToString(blockAddr), err)
			}
		}
	}

	// Start read portion
	readBlock := make([]byte, BLOCK_SIZE)
	for blockAddr := uint64(0); blockAddr < devSize; blockAddr += BLOCK_SIZE {
		statusFunc(name, "read", blockAddr, devSize, &res)
		if _, err := fp.Seek(int64(blockAddr), os.SEEK_SET); err != nil {
			res.failedReadAddrs = append(res.failedReadAddrs, blockAddr)
			if res.firstFailedRead == nil {
				res.firstFailedRead = fmt.Errorf("Error seeking to %#0x (%s): %w", blockAddr, szToString(blockAddr), err)
			}
			continue
		}
		blockData := makeBlock(blockAddr, BLOCK_SIZE)
		if _, err := fp.Read(readBlock); err != nil {
			res.failedReadAddrs = append(res.failedReadAddrs, blockAddr)
			if res.firstFailedRead == nil {
				res.firstFailedRead = fmt.Errorf("Error reading at %#0x (%s): %w", blockAddr, szToString(blockAddr), err)
			}
			continue
		}
		if !bytes.Equal(readBlock, blockData) {
			res.failedReadAddrs = append(res.failedReadAddrs, blockAddr)
			if res.firstFailedRead == nil {
				res.firstFailedRead = fmt.Errorf("Error reading at %#0x (%s): data incorrect", blockAddr, szToString(blockAddr))
			}
			continue
		}
	}

	return &res, nil
}

func makeBlock(base, size uint64) []byte {
	block := make([]byte, size)
	for i := uint64(0); i < size; i += uint64(WORD_SIZE) {
		binary.LittleEndian.PutUint64(block[i:], base+i)
	}
	return block
}

func GetDeviceSize64(name string) (uint64, error) {
	fp, err := os.Open(name)
	if err != nil {
		return 0, err
	}
	defer fp.Close()
	return getDeviceSize64(fp)
}

func getDeviceSize64(fp *os.File) (uint64, error) {
	var sz uint64
	if _, _, err := syscall.Syscall(syscall.SYS_IOCTL, fp.Fd(), unix.BLKGETSIZE64, uintptr(unsafe.Pointer(&sz))); err != 0 {
		return 0, os.NewSyscallError("ioctl: BLKGETSIZE64", err)
	}
	return sz, nil
}

// Make a function to get a string size
func MakeSizeFunc(binary bool) sizeStringer {
	prefixes := []string{"", "K", "M", "G", "T", "P"}
	base := uint64(1000)
	mid := ""
	if binary {
		base = 1024
		mid = "i"
	}
	// TODO: support a decimal length
	return func(sz uint64) string {
		szo := sz
		for i := 0; i < len(prefixes); i++ {
			if sz < base || i == len(prefixes)-1 {
				pfx := prefixes[i]
				if pfx == "" {
					mid = ""
				}
				return fmt.Sprintf("%d %s%sB", sz, pfx, mid)
			}
			sz /= base
		}
		return fmt.Sprintf("%d B", szo)
	}
}

func formatAddrList(a []uint64) string {
	n := len(a)
	suff := ""
	if n > MAX_ADDRS {
		n = MAX_ADDRS
		suff = ", ..."
	}
	var al []string
	for i := 0; i < n; i++ {
		al = append(al, fmt.Sprintf("%#0x", a[i]))
	}
	return fmt.Sprintf("[%s%s]", strings.Join(al, ", "), suff)
}

func clearCurrentLine() {
	fmt.Print("\033[2K\033[G")
}

func makeStatusFunc(szToString sizeStringer) statusCallback {
	started := time.Now()
	lastUpdated := started
	lastRead := uint64(0)
	return func(dev, op string, pos, size uint64, rep *TestReport) {
		now := time.Now()
		// time in future ?
		if lastUpdated.Add(STATUS_INTERVAL).After(now) {
			return
		}
		speed := (pos - lastRead) / uint64(now.Sub(lastUpdated).Seconds())
		lastUpdated = now
		spent := uint64(now.Sub(started).Seconds())
		clearCurrentLine()
		fmt.Printf("[%03ds] %s: %s: %s/%s (%s/s)", spent, dev, op, szToString(pos), szToString(size), szToString(speed))
	}
}
