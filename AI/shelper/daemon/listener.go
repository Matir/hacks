package daemon

import (
	"context"
	"fmt"
	"net"
	"os"
	"sync"
	"time"

	"shelper/log"
)

// Daemon represents the background service daemon.
type Daemon struct {
	socketPath    string
	listener      net.Listener
	wg            sync.WaitGroup
	ctx           context.Context
	cancel        context.CancelFunc
	reqHandler    func(context.Context, *SocketRequest) (*SocketResponse, error)
	startTime     time.Time
	activeWorkers int32
	totalRequests int64
	logger        *log.Logger
}

// NewDaemon initializes a new daemon instance with a custom logger.
func NewDaemon(socketPath string, handler func(context.Context, *SocketRequest) (*SocketResponse, error), logger *log.Logger) *Daemon {
	ctx, cancel := context.WithCancel(context.Background())
	return &Daemon{
		socketPath: socketPath,
		ctx:        ctx,
		cancel:     cancel,
		reqHandler: handler,
		startTime:  time.Now(),
		logger:     logger,
	}
}

// Start binds to the Unix socket and begins accepting client connections.
func (d *Daemon) Start() error {
	// Clean up existing socket file if it exists
	if _, err := os.Stat(d.socketPath); err == nil {
		if err := os.Remove(d.socketPath); err != nil {
			return fmt.Errorf("failed to remove existing socket file: %w", err)
		}
	}

	listener, err := net.Listen("unix", d.socketPath)
	if err != nil {
		return fmt.Errorf("failed to listen on Unix domain socket: %w", err)
	}
	d.listener = listener

	// Ensure the socket has read/write permissions for the current user
	if err := os.Chmod(d.socketPath, 0600); err != nil {
		d.listener.Close()
		return fmt.Errorf("failed to set socket file permissions: %w", err)
	}

	d.logger.Info("Listening on unix socket: %s", d.socketPath)

	d.wg.Add(1)
	go d.acceptLoop()

	return nil
}

// acceptLoop continuously accepts incoming client connections until the daemon is stopped.
func (d *Daemon) acceptLoop() {
	defer d.wg.Done()

	for {
		conn, err := d.listener.Accept()
		if err != nil {
			select {
			case <-d.ctx.Done():
				return // Closed normally
			default:
				d.logger.Error("Failed to accept connection: %v", err)
				continue
			}
		}

		d.wg.Add(1)
		go func(c net.Conn) {
			defer d.wg.Done()
			defer c.Close()
			d.handleConnection(c)
		}(conn)
	}
}

// Stop signals the daemon to shut down gracefully.
func (d *Daemon) Stop() {
	d.cancel()
	if d.listener != nil {
		d.listener.Close()
	}
	d.wg.Wait()
	os.Remove(d.socketPath)
	d.logger.Info("Daemon stopped cleanly")
}
