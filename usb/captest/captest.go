package main

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"io"
	"log"
	"os"
	"strings"
)

func main() {
	if len(os.Args) != 2 {
		usage()
	}
	device := os.Args[1]
	size, err := deviceSize(device)
	if err != nil {
		log.Printf("Error getting size: %v", err)
		usage()
	}
	if !confirm(device, size) {
		fmt.Println("Aborting...")
		return
	}
	log.Printf("Starting process to write blocks.")
	if err := writeDevice(device, size); err != nil {
		log.Printf("Error writing device... %v", err)
		os.Exit(1)
	}
	log.Printf("Reading device back to verify.")
	if err := readDevice(device, size); err != nil {
		log.Printf("Error reading back: %v", err)
		os.Exit(1)
	}
	fmt.Println("Everything ok!")
}

func usage() {
	fmt.Printf("%s <device>\n", os.Args[0])
	os.Exit(1)
}

func confirm(devName string, sz int64) bool {
	fmt.Printf("This will overwrite all data on %s (%s), continue? ", devName, deviceSizeString(sz))
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Scan()
	buf := scanner.Text()
	return strings.ToLower(buf) == "yes"
}

func deviceSize(devName string) (int64, error) {
	fp, err := os.Open(devName)
	if err != nil {
		return 0, err
	}
	defer fp.Close()
	pos, err := fp.Seek(0, io.SeekEnd)
	if err != nil {
		return 0, err
	}
	return pos, nil
}

func deviceSizeString(sz int64) string {
	const unit = int64(1024)
	if sz < unit {
		return fmt.Sprintf("%d B", sz)
	}
	div, exp := unit, 0
	for n := sz / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.2f %ciB", float64(sz)/float64(div), "KMGTPE"[exp])
}

func writeDevice(devname string, sz int64) error {
	fp, err := os.OpenFile(devname, os.O_RDWR, 0)
	if err != nil {
		return err
	}
	defer fp.Close()
	buffp := bufio.NewWriter(fp)
	defer buffp.Flush()
	blockSz := int64(8)
	for i := int64(0); i < sz/blockSz; i++ {
		if err := binary.Write(buffp, binary.BigEndian, i); err != nil {
			return err
		}
	}
	return nil
}

func readDevice(devname string, sz int64) error {
	fp, err := os.Open(devname)
	if err != nil {
		return err
	}
	defer fp.Close()
	buffp := bufio.NewReader(fp)
	blockSz := int64(8)
	var dest int64
	for i := int64(0); i < sz/blockSz; i++ {
		if err := binary.Read(buffp, binary.BigEndian, &dest); err != nil {
			return err
		}
		if dest != i {
			return fmt.Errorf("Expected %x, read %x.", i, dest)
		}
	}
	return nil
}
