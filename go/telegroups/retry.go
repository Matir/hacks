package main

import (
	"errors"
	"strconv"
	"strings"
	"time"

	"github.com/zelenin/go-tdlib/client"
)

// withFloodWait calls fn and transparently retries if TDLib responds with a
// 429 flood-wait error, sleeping for the duration specified in the response.
// Any other error is returned immediately.
func withFloodWait(fn func() error) error {
	for {
		err := fn()
		if err == nil {
			return nil
		}
		wait, ok := floodWaitDuration(err)
		if !ok {
			return err
		}
		logInfo("flood wait: sleeping %v", wait)
		time.Sleep(wait)
	}
}

func floodWaitDuration(err error) (time.Duration, bool) {
	var tdErr *client.Error
	if !errors.As(err, &tdErr) || tdErr.Code != 429 {
		return 0, false
	}
	secs := parseRetryAfter(tdErr.Message)
	return time.Duration(secs+1) * time.Second, true
}

// parseRetryAfter extracts the wait seconds from a TDLib flood-wait message
// of the form "Too Many Requests: retry after N".
func parseRetryAfter(msg string) int {
	const marker = "retry after "
	if i := strings.LastIndex(msg, marker); i >= 0 {
		if n, err := strconv.Atoi(strings.TrimSpace(msg[i+len(marker):])); err == nil && n > 0 {
			return n
		}
	}
	return 5 // safe default
}
