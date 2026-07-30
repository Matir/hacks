package daemon

import (
	"bufio"
	"context"
	"encoding/json"
	"net"
	"os"
	"path/filepath"
	"shelper/log"
	"sync/atomic"
	"testing"
	"time"
)

func TestDaemonStatusTracking(t *testing.T) {
	tmpDir := t.TempDir()
	sockPath := filepath.Join(tmpDir, "test.sock")

	// Wait helper channel
	requestStarted := make(chan struct{})
	requestBlock := make(chan struct{})

	// Custom handler that blocks so we can measure active workers
	handler := func(ctx context.Context, req *SocketRequest) (*SocketResponse, error) {
		close(requestStarted)
		<-requestBlock
		return &SocketResponse{
			ID:     req.ID,
			Status: "success",
			Output: "done",
		}, nil
	}

	d := NewDaemon(sockPath, handler, log.NewLogger(os.Stdout, "error"))
	if err := d.Start(); err != nil {
		t.Fatalf("failed to start daemon: %v", err)
	}
	defer d.Stop()

	// 1. Verify initial status via status query
	conn, err := net.Dial("unix", sockPath)
	if err != nil {
		t.Fatalf("dial failed: %v", err)
	}

	statusReq := SocketRequest{
		ID:   "status-1",
		Type: "status",
	}
	reqData, _ := json.Marshal(statusReq)
	conn.Write(append(reqData, '\n'))

	scanner := bufio.NewScanner(conn)
	if !scanner.Scan() {
		t.Fatalf("failed to read initial status response")
	}

	var statusResp SocketResponse
	json.Unmarshal(scanner.Bytes(), &statusResp)

	if statusResp.ID != "status-1" {
		t.Errorf("expected ID 'status-1', got %q", statusResp.ID)
	}

	var telemetry map[string]interface{}
	if err := json.Unmarshal([]byte(statusResp.Output), &telemetry); err != nil {
		t.Fatalf("failed to parse status output: %v", err)
	}

	if telemetry["status"] != "active" {
		t.Errorf("expected status 'active', got %q", telemetry["status"])
	}
	if telemetry["active_workers"].(float64) != 0 {
		t.Errorf("expected active_workers to be 0, got %v", telemetry["active_workers"])
	}
	conn.Close()

	// 2. Start a blocking request on a new connection to check active workers
	conn2, err := net.Dial("unix", sockPath)
	if err != nil {
		t.Fatalf("dial failed: %v", err)
	}
	defer conn2.Close()

	workReq := SocketRequest{
		ID:    "work-1",
		Input: "generate code",
	}
	workData, _ := json.Marshal(workReq)
	conn2.Write(append(workData, '\n'))

	// Wait until the handler actually begins
	<-requestStarted

	// Check active workers count
	workersVal := atomic.LoadInt32(&d.activeWorkers)
	if workersVal != 1 {
		t.Errorf("expected 1 active worker, got %d", workersVal)
	}

	// 3. Simultaneously query status again to check reported telemetry active workers
	conn3, err := net.Dial("unix", sockPath)
	if err != nil {
		t.Fatalf("dial failed: %v", err)
	}
	defer conn3.Close()

	conn3.Write(append(reqData, '\n'))
	scanner3 := bufio.NewScanner(conn3)
	if scanner3.Scan() {
		var statusResp2 SocketResponse
		json.Unmarshal(scanner3.Bytes(), &statusResp2)
		var telemetry2 map[string]interface{}
		json.Unmarshal([]byte(statusResp2.Output), &telemetry2)

		// The active worker processing work-1 should be reflected in active_workers
		if telemetry2["active_workers"].(float64) != 1 {
			t.Errorf("expected reported active_workers to be 1, got %v", telemetry2["active_workers"])
		}
	}

	// Unblock request and verify active workers drops back to 0
	close(requestBlock)

	// Wait for response of work-1
	scanner2 := bufio.NewScanner(conn2)
	if !scanner2.Scan() {
		t.Fatalf("failed to read work response")
	}

	// Give a tiny moment for worker decrement to execute after handler return
	time.Sleep(10 * time.Millisecond)

	workersVal2 := atomic.LoadInt32(&d.activeWorkers)
	if workersVal2 != 0 {
		t.Errorf("expected active workers to return to 0, got %d", workersVal2)
	}
}
