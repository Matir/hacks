// Convert Ubisoft XBT Textures to Microsoft DDS
package main

import (
	"bufio"
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

const (
	XBTExtension = ".xbt"
	DDSExtension = ".dds"
)

var (
	MAGIC                = []byte("TBX")
	ErrorInvalidMagic    = errors.New("Invalid Magic!")
	ErrorReadFailed      = errors.New("Read failed!")
	ErrorUnknownFileType = errors.New("Unknown file type")
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <path> ...\n", os.Args[0])
		os.Exit(2)
	}
	for _, p := range os.Args[1:] {
		if err := handlePath(p); err != nil {
			fmt.Fprintf(os.Stderr, "Fatal error for path %s: %s\n", p, err)
			os.Exit(1)
		}
	}
}

func handlePath(inpath string) error {
	finfo, err := os.Stat(inpath)
	if err != nil {
		return err
	}
	if finfo.IsDir() {
		return filepath.Walk(inpath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			if info.Mode().IsRegular() && strings.HasSuffix(path, XBTExtension) {
				return handleFile(path)
			}
			return nil
		})
	} else if finfo.Mode().IsRegular() {
		return handleFile(inpath)
	}
	return ErrorUnknownFileType
}

func handleFile(inpath string) error {
	outpath := makeOutPath(inpath)
	if err := convertSingleFile(inpath, outpath); err != nil {
		fmt.Fprintf(os.Stderr, "Error convering file %s: %s\n", inpath, err)
		return err
	}
	fmt.Printf("%s -> %s\n", inpath, outpath)
	return nil
}

func makeOutPath(inpath string) string {
	if strings.HasSuffix(inpath, XBTExtension) {
		return inpath[:len(inpath)-len(XBTExtension)] + DDSExtension
	}
	return inpath + DDSExtension
}

func convertSingleFile(inpath, outpath string) error {
	infp, err := os.Open(inpath)
	if err != nil {
		return err
	}
	defer infp.Close()

	// Read the header
	rdr := bufio.NewReader(infp)
	magic := make([]byte, len(MAGIC))
	if n, err := rdr.Read(magic); err != nil {
		return err
	} else if n != len(MAGIC) {
		return ErrorInvalidMagic
	}
	if !bytes.Equal(MAGIC, magic) {
		return ErrorInvalidMagic
	}
	version, err := rdr.ReadByte()
	if version != byte(0) {
		return ErrorInvalidMagic
	}
	// Discard unknown field
	if _, err := rdr.Discard(4); err != nil {
		return err
	}
	// Read length field
	var hdrlen uint32
	if err := binary.Read(rdr, binary.LittleEndian, &hdrlen); err != nil {
		return nil
	}

	// Reset the reader
	if n, err := infp.Seek(int64(hdrlen), 0); err != nil {
		return err
	} else if n != int64(hdrlen) {
		return ErrorReadFailed
	}
	rdr.Reset(infp)

	// Prepare the writer
	outfp, err := os.OpenFile(outpath, os.O_RDWR|os.O_CREATE|os.O_EXCL, 0640)
	if err != nil {
		return err
	}
	defer func() {
		outfp.Sync()
		outfp.Close()
	}()

	// Make the copy
	if _, err := io.Copy(outfp, rdr); err != nil {
		return err
	}
	return nil
}
