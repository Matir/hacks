package glesspipe

import (
	"io"
)

type FilterScore int

const (
	FilterScoreNoMatch FilterScore = iota
	FilterScoreWeakMatch
	FilterScoreFullMatch
)

// These are glesspipe filters.  The highest scoring filter is used.
// Currently only a single level of filter is supported, but this may be
// extended in the future.
type Filter interface {
	// How long we need to be able to decide if this filter applies
	PeekLen() int
	// Score the provided buffer (filename optional)
	Score(string, []byte) FilterScore
	// Take a reader and produce filtered output
	Apply(io.Reader) io.Reader
	// Describe ourselves
	Name() string
}

// An implementation of io.Reader that allows peaking at the first x bytes
type FilterSource struct {
	// Underlying source
	source io.Reader
	// Prefix buffer
	buf []byte
	pos uint64
}

func NewFilterSource(rdr io.Reader, bufferlen int) (*FilterSource, error) {
	rv := &FilterSource{
		buf:    make([]byte, bufferlen),
		source: rdr,
		pos:    0,
	}
	n, err := rdr.Read(rv.buf)
	if err != nil {
		return nil, err
	}
	rv.buf = rv.buf[:n]
	return rv, nil
}

func (fs *FilterSource) Read(p []byte) (int, error) {
	// Some part should be read from the buffer
	copied := 0
	if fs.pos < uint64(len(fs.buf)) {
		copied = copy(p, fs.buf[fs.pos:])
		fs.pos += uint64(copied)
	}
	if copied < len(p) {
		n, err := fs.source.Read(p[copied:])
		copied += n
		if err != nil {
			return copied, err
		}
	}
	return copied, nil
}

// Get a copy of the underlying buffer to peek
func (fs *FilterSource) Peek() []byte {
	rv := make([]byte, len(fs.buf))
	copy(rv, fs.buf)
	return rv
}
