package main

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"runtime/pprof"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unsafe"

	"github.com/brk0v/directio"
	"golang.org/x/sys/unix"
)

const (
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
	os.Exit(real_main())
}

// This is used for early return honoring defer
func real_main() int {
	noConfirmFlag := flag.Bool("dangerous-no-confirm", false, "Skip confirmation!")
	binaryFlag := flag.Bool("binary", false, "Use binary sizes.")
	cpuprofileFlag := flag.String("profile", "", "Log cpu profile.")
	bufSizeFlag := flag.String("bufsize", "4k", "Buffer size, suffixes K/M/G supported.")

	flag.Parse()

	args := flag.CommandLine.Args()
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Device not specified!\n")
		flag.Usage()
		return 1
	}

	bufSize, err := parseSize(*bufSizeFlag)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing buffer size: %v\n", err)
		flag.Usage()
		return 1
	}

	devName := args[0]

	if *cpuprofileFlag != "" {
		f, err := os.Create(*cpuprofileFlag)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Can't start profile: %s\n", err)
			return 1
		}
		pprof.StartCPUProfile(f)
		defer pprof.StopCPUProfile()
	}

	devSize, err := GetDeviceSize64(devName)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting device size: %s\n", err)
		return 1
	}
	szToString := MakeSizeFunc(*binaryFlag, 3)

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
			return 1
		}
		if strings.TrimSpace(sc.Text()) != "YES" {
			fmt.Fprintln(os.Stderr, "Confirmation not given, aborting!")
			return 1
		}
	}

	sigch := make(chan os.Signal, 1)
	stopChan := make(chan bool)
	go func() {
		<-sigch
		fmt.Fprintf(os.Stderr, "Interrupt received, stopping, press CTRL+C again to hard abort.\n")
		os.Stderr.Sync()
		stopChan <- true
		<-sigch
		fmt.Fprintf(os.Stderr, "2nd interrupt, aborting!\n")
		os.Stderr.Sync()
		os.Exit(1)
	}()
	signal.Notify(sigch, syscall.SIGINT)

	rv := 0
	if res, err := PerformWriteReadTest(devName, devSize, szToString, stopChan, bufSize); err != nil {
		fmt.Fprintf(os.Stderr, "Error in performing test: %s\n", err)
		return 1
	} else if res != nil {
		if res.firstFailedWrite != nil {
			fmt.Printf("First write error: %v\n", res.firstFailedWrite)
			rv = 1
		}
		if res.firstFailedRead != nil {
			fmt.Printf("First read error: %v\n", res.firstFailedRead)
			rv = 1
		}
		if res.failedWriteAddrs != nil && len(res.failedWriteAddrs) > 0 {
			fmt.Printf("%d write errors: %s\n", len(res.failedWriteAddrs), formatAddrList(res.failedWriteAddrs))
			rv = 1
		}
		if res.failedReadAddrs != nil && len(res.failedReadAddrs) > 0 {
			fmt.Printf("%d read errors: %s\n", len(res.failedReadAddrs), formatAddrList(res.failedReadAddrs))
			rv = 1
		}
		if rv == 0 {
			fmt.Printf("Test succeeded, %s okay\n", szToString(devSize))
		}
	} else {
		fmt.Fprintf(os.Stderr, "Error in test: no error, no report!\n")
		return 1
	}
	return rv
}

func PerformWriteReadTest(name string, devSize uint64, szToString sizeStringer, stopChan <-chan bool, bufSize int) (*TestReport, error) {
	checkStop := func() bool {
		select {
		case <-stopChan:
			return true
		default:
			return false
		}
	}
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

	dio, err := directio.NewSize(fp, bufSize)
	if err != nil {
		return nil, fmt.Errorf("Error creating directio: %w", err)
	}

	var res TestReport

	// Start write portion
	for blockAddr := uint64(0); blockAddr < devSize; blockAddr += uint64(bufSize) {
		statusFunc(name, "write", blockAddr, devSize, &res)
		if checkStop() {
			return nil, fmt.Errorf("Aborted in write test.")
		}
		if _, err := fp.Seek(int64(blockAddr), os.SEEK_SET); err != nil {
			res.failedWriteAddrs = append(res.failedWriteAddrs, blockAddr)
			if res.firstFailedWrite == nil {
				res.firstFailedWrite = fmt.Errorf("Error seeking to %#0x (%s): %w", blockAddr, szToString(blockAddr), err)
			}
			continue
		}
		thisBufSize := uint64(bufSize)
		if uint64(bufSize) > (devSize - blockAddr) {
			thisBufSize = devSize - blockAddr
		}
		blockData := makeBlock(blockAddr, thisBufSize)
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
	fmt.Println("")
	readBlock := make([]byte, bufSize)
	for blockAddr := uint64(0); blockAddr < devSize; blockAddr += uint64(bufSize) {
		if checkStop() {
			return nil, fmt.Errorf("Aborted in read test.")
		}
		statusFunc(name, "read", blockAddr, devSize, &res)
		if _, err := fp.Seek(int64(blockAddr), os.SEEK_SET); err != nil {
			res.failedReadAddrs = append(res.failedReadAddrs, blockAddr)
			if res.firstFailedRead == nil {
				res.firstFailedRead = fmt.Errorf("Error seeking to %#0x (%s): %w", blockAddr, szToString(blockAddr), err)
			}
			continue
		}
		thisBufSize := uint64(bufSize)
		if uint64(bufSize) > (devSize - blockAddr) {
			thisBufSize = devSize - blockAddr
			if uint64(len(readBlock)) > thisBufSize {
				readBlock = readBlock[:thisBufSize]
			} else {
				readBlock = make([]byte, thisBufSize)
			}
		}
		blockData := makeBlock(blockAddr, thisBufSize)
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

	fmt.Println("")
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
func MakeSizeFunc(binary bool, nfigs int) sizeStringer {
	prefixes := []string{"", "K", "M", "G", "T", "P"}
	base := uint64(1000)
	mid := ""
	if binary {
		base = 1024
		mid = "i"
	}

	// Handle decimal length case
	if nfigs > 0 {
		return func(sz uint64) string {
			szf := float64(sz)
			szo := sz
			for i := 0; i < len(prefixes); i++ {
				if szf < float64(base) || i == len(prefixes)-1 {
					pfx := prefixes[i]
					if pfx == "" {
						mid = ""
					}
					return fmt.Sprintf("%.*g %s%sB", nfigs, szf, pfx, mid)
				}
				szf /= float64(base)
			}
			return fmt.Sprintf("%d B", szo)
		}
	}

	// Integer case, nfigs == 0
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
	avg := NewRollingAverager(8)
	return func(dev, op string, pos, size uint64, rep *TestReport) {
		now := time.Now()
		// time in future ?
		if lastUpdated.Add(STATUS_INTERVAL).After(now) {
			return
		}
		if lastRead > pos {
			lastRead = pos
		}
		speed := (pos - lastRead) / uint64(now.Sub(lastUpdated).Seconds())
		avgSpeed := avg.Add(speed)
		lastUpdated = now
		lastRead = pos
		spent := uint64(now.Sub(started).Seconds())
		clearCurrentLine()
		fmt.Printf("[%03ds] %s: %s: %s/%s (%s/s)", spent, dev, op, szToString(pos), szToString(size), szToString(avgSpeed))
	}
}

func parseSize(szstr string) (int, error) {
	suffixes := map[string]int{
		"k": 1024,
		"m": 1024 * 1024,
		"g": 1024 * 1024 * 1024,
		"K": 1024,
		"M": 1024 * 1024,
		"G": 1024 * 1024 * 1024,
	}
	mul := 1
	for s, m := range suffixes {
		if strings.HasSuffix(szstr, s) {
			mul = m
			szstr = strings.TrimSuffix(szstr, s)
			break
		}
	}
	n, err := strconv.ParseInt(szstr, 0, 32)
	if err != nil {
		return 0, err
	}
	return int(n) * mul, nil
}

type RollingAverager struct {
	samples []uint64
	next    int
}

func NewRollingAverager(size int) *RollingAverager {
	return &RollingAverager{
		samples: make([]uint64, 0, size),
	}
}

func (ra *RollingAverager) Add(v uint64) uint64 {
	if len(ra.samples) <= ra.next {
		ra.samples = append(ra.samples, v)
	} else {
		ra.samples[ra.next] = v
	}
	ra.next += 1
	ra.next %= cap(ra.samples)
	return ra.Avg()
}

func (ra *RollingAverager) Avg() uint64 {
	sum := uint64(0)
	for _, v := range ra.samples {
		sum += v
	}
	return sum / uint64(len(ra.samples))
}
