package daemon

import (
	"bufio"
	"context"
	"encoding/json"
	"net"
	"sync/atomic"
	"time"
)

// handleConnection processes client requests sent over a connection.
func (d *Daemon) handleConnection(conn net.Conn) {
	scanner := bufio.NewScanner(conn)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var req SocketRequest
		if err := json.Unmarshal(line, &req); err != nil {
			d.logger.Error("JSON unmarshal failed: %v", err)
			d.writeErrorResponse(conn, "", "INVALID_REQUEST", "JSON unmarshal failed", err.Error())
			continue
		}

		// Increment request stats
		atomic.AddInt64(&d.totalRequests, 1)

		// Handle status requests internally
		if req.Type == "status" {
			d.logger.Info("Received health status query (req ID: %s)", req.ID)
			d.writeStatusResponse(conn, req.ID)
			continue
		}

		// Track active background workers
		atomic.AddInt32(&d.activeWorkers, 1)

		// Process normal text generation request in a closure to safely defer telemetry decrement
		resp, err := func() (*SocketResponse, error) {
			defer atomic.AddInt32(&d.activeWorkers, -1)
			ctx, cancel := context.WithTimeout(d.ctx, 60*time.Second)
			defer cancel()
			return d.reqHandler(ctx, &req)
		}()

		if err != nil {
			d.logger.Error("Request processing failed: %v", err)
			d.writeErrorResponse(conn, req.ID, "SYSTEM_ERROR", "Request processing failed", err.Error())
			continue
		}

		// Write response to socket
		d.writeResponse(conn, resp)
	}

	if err := scanner.Err(); err != nil {
		d.logger.Error("Scan connection error: %v", err)
	}
}

// writeResponse serializes and transmits the response back to the client.
func (d *Daemon) writeResponse(conn net.Conn, resp *SocketResponse) {
	data, err := json.Marshal(resp)
	if err != nil {
		d.logger.Error("Marshal response error: %v", err)
		return
	}
	conn.Write(append(data, '\n'))
}

// writeErrorResponse helper constructs and sends an error envelope.
func (d *Daemon) writeErrorResponse(conn net.Conn, id, code, message, details string) {
	resp := &SocketResponse{
		ID:     id,
		Status: "error",
		Error: &ResponseError{
			Code:    code,
			Message: message,
			Details: details,
		},
		Metadata: ResponseMetadata{
			Provider:       "none",
			Model:          "none",
			TemplateSource: "none",
		},
	}
	d.writeResponse(conn, resp)
}

// writeStatusResponse constructs and transmits telemetry stats.
func (d *Daemon) writeStatusResponse(conn net.Conn, id string) {
	uptime := time.Since(d.startTime).Seconds()
	workers := atomic.LoadInt32(&d.activeWorkers)
	requests := atomic.LoadInt64(&d.totalRequests)

	statusInfo := map[string]interface{}{
		"status":         "active",
		"uptime":         uptime,
		"active_workers": workers,
		"total_requests": requests,
	}

	outputBytes, _ := json.Marshal(statusInfo)

	resp := &SocketResponse{
		ID:     id,
		Status: "success",
		Output: string(outputBytes),
		Metadata: ResponseMetadata{
			Provider:       "internal",
			Model:          "none",
			TemplateSource: "none",
		},
	}
	d.writeResponse(conn, resp)
}
