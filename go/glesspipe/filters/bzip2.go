package filters

import (
	"bytes"
	"compress/gzip"
	"io"
)

var BZIP_MAGIC = []byte("BZh")
var BZIP_C_MAGIC = []byte{0x31, 0x41, 0x59, 0x26, 0x53, 0x59}

type Bzip2Filter struct {
}

func (gf Bzip2Filter) PeekLen() int {
	return len(BZIP_MAGIC) + 1 + len(BZIP_C_MAGIC)
}

func (gf Bzip2Filter) Score(name string, buf []byte) FilterScore {
	if bytes.Equal(BZIP_MAGIC[:], buf[:len(BZIP_MAGIC)]) {
		// double check
		if bytes.Equal(BZIP_C_MAGIC, buf[3:3+len(BZIP_C_MAGIC)]) {
			return FilterScoreFullMatch
		}
	}
	return FilterScoreNoMatch
}

func (gf Bzip2Filter) Apply(rdr io.Reader) (io.Reader, error) {
	return gzip.NewReader(rdr)
}

func (gf Bzip2Filter) Name() string {
	return "gzip"
}
