package recorder

import (
	"encoding/json"
	"io"
	"os"
	"sync"
)

// Writer formats TrafficRecords into JSON Lines (jsonl) and writes them to a sink sink safely across goroutines.
type Writer struct {
	mu   sync.Mutex
	sink io.Writer
}

// NewWriter creates a new JSONL recorder targeting the specified file path or stdout if "-" or empty.
func NewWriter(filePath string) (*Writer, error) {
	if filePath == "" || filePath == "-" {
		return &Writer{sink: os.Stdout}, nil
	}
	f, err := os.OpenFile(filePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		return nil, err
	}
	return &Writer{sink: f}, nil
}

// WriteRecord serializes a TrafficRecord to JSON Line format and appends it to the sink.
func (w *Writer) WriteRecord(rec *TrafficRecord) error {
	data, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	data = append(data, '\n')

	w.mu.Lock()
	defer w.mu.Unlock()
	_, err = w.sink.Write(data)
	return err
}

// Close closes the underlying sink file if applicable.
func (w *Writer) Close() error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if closer, ok := w.sink.(io.Closer); ok && w.sink != os.Stdout && w.sink != os.Stderr {
		return closer.Close()
	}
	return nil
}
