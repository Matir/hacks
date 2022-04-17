package filters

import (
	"bytes"
	"compress/gzip"
	"io"
)

var GZIP_MAGIC = [...]byte{0x1f, 0x8b}

type GzipFilter struct {
}

func (gf GzipFilter) PeekLen() int {
	return len(GZIP_MAGIC)
}

func (gf GzipFilter) Score(name string, buf []byte) FilterScore {
	if bytes.Equal(GZIP_MAGIC[:], buf[:len(GZIP_MAGIC)]) {
		return FilterScoreFullMatch
	}
	return FilterScoreNoMatch
}

func (gf GzipFilter) Apply(rdr io.Reader) (io.Reader, error) {
	return gzip.NewReader(rdr)
}

func (gf GzipFilter) Name() string {
	return "gzip"
}
