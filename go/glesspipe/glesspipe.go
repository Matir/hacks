package glesspipe

import (
	"io"

	"github.com/Matir/hacks/go/glesspipe/filters"
)

type GlessPipe struct {
	registeredFilters []Filter
}

func NewGlessPipe() *GlessPipe {
	return &GlessPipe{
		registeredFilters: []Filter{
			filters.GzipFilter{},
			filters.Bzip2Filter{},
		},
	}
}

func (gp *GlessPipe) Run(name string, rdr io.Reader, writer io.Writer) error {
	src, err := NewFilterSource(rdr, gp.getPeekLen())
	if err != nil {
		return err
	}
	if filter := gp.findBestFilter(name, src); filter != nil {
		newReader, err := filter.Apply(src)
		if err != nil {
			return err
		}
		_, err = io.Copy(writer, newReader)
		return err
	}
	_, err = io.Copy(writer, src)
	return err
}

func (gp *GlessPipe) findBestFilter(name string, src *FilterSource) Filter {
	strength := filters.FilterScoreNoMatch
	var which Filter
	peekBuf := src.Peek()
	for _, v := range gp.registeredFilters {
		sc := v.Score(name, peekBuf)
		if sc > strength {
			which = v
		}
	}
	return which
}

func (gp *GlessPipe) getPeekLen() int {
	peekLen := 0
	for _, v := range gp.registeredFilters {
		pl := v.PeekLen()
		if pl > peekLen {
			peekLen = pl
		}
	}
	return peekLen
}
