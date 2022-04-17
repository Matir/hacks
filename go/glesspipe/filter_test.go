package glesspipe

import (
	"bytes"
	"errors"
	"io"
	"testing"
)

const testData = `abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`

func TestFilterSource(t *testing.T) {
	testBuf := bytes.NewBuffer([]byte(testData))
	rdr, err := NewFilterSource(testBuf, 10)
	if err != nil {
		t.Fatalf("Error creating filter source!")
	}
	buf := make([]byte, 62)
	if n, err := rdr.Read(buf); err != nil {
		t.Fatalf("Expected to read 62, got error: %v", err)
	} else if n != 62 {
		t.Fatalf("Expected to read 62, got %d", n)
	} else if string(buf[:n]) != testData {
		t.Fatalf("Unexpected response: %v", string(buf))
	}
}

func TestFilterSource_PrereadLonger(t *testing.T) {
	testBuf := bytes.NewBuffer([]byte(testData))
	rdr, err := NewFilterSource(testBuf, 100)
	if err != nil {
		t.Fatalf("Error creating filter source!")
	}
	buf := make([]byte, 62)
	if n, err := rdr.Read(buf); err != nil {
		t.Fatalf("Expected to read 62, got error: %v", err)
	} else if n != 62 {
		t.Fatalf("Expected to read 62, got %d", n)
	} else if string(buf[:n]) != testData {
		t.Fatalf("Unexpected response: %v", string(buf))
	}
}

func TestFilterSource_ReadLonger(t *testing.T) {
	testBuf := bytes.NewBuffer([]byte(testData))
	rdr, err := NewFilterSource(testBuf, 10)
	if err != nil {
		t.Fatalf("Error creating filter source!")
	}
	buf := make([]byte, 100)
	if n, err := rdr.Read(buf); err != nil {
		t.Fatalf("Expected to read 62, got error: %v", err)
	} else if n != 62 {
		t.Fatalf("Expected to read 62, got %d", n)
	} else if string(buf[:n]) != testData {
		t.Fatalf("Unexpected response: %v", string(buf))
	}
}

func TestFilterSource_ReadChunks(t *testing.T) {
	testBuf := bytes.NewBuffer([]byte(testData))
	rdr, err := NewFilterSource(testBuf, 10)
	if err != nil {
		t.Fatalf("Error creating filter source!")
	}
	buf := make([]byte, 100)
	csize := 10
	totRead := 0
	for i := 0; i < len(buf); i += csize {
		if n, err := rdr.Read(buf[i : i+csize]); err != nil {
			if errors.Is(err, io.EOF) && totRead == len(testData) {
				continue
			}
			t.Fatalf("Expected to read, got error: %v", err)
		} else if n != csize && totRead+n != len(testData) {
			t.Fatalf("Expected to read %d, got %d", csize, n)
		} else {
			totRead += n
		}
	}
	if string(buf[:len(testData)]) != testData {
		t.Fatalf("Unexpected response: %v", string(buf))
	}
}
