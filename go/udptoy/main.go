package main

import (
	"errors"
	"flag"
	"log"
	"net"
	"os"
	"sync"
	"time"
)

const (
	ReceiveTimeout = 1 * time.Second
	GCInterval     = 5 * time.Minute
	GCDelay        = 1 * time.Hour
)

var (
	listenAddrFlag = flag.String("listen", "0.0.0.0:9999", "Address on which to listen.")
	destAddrFlag   = flag.String("dest", "", "Destination to which datagrams should be forwarded.")
	maxDgramSize   = flag.Int("maxsize", 65535, "Maximum datagram size.")
)

type ListenMux struct {
	listenAddr *net.UDPAddr
	listenSock *net.UDPConn
	destAddr   *net.UDPAddr
	mapLock    sync.Mutex
	workers    map[string]*UDPConnWorker
	bufSize    int
}

type UDPConnWorker struct {
	peer         *net.UDPAddr
	dest         *net.UDPAddr
	conn         *net.UDPConn
	incoming     chan []byte
	responses    chan []byte
	wg           sync.WaitGroup
	lastActivity time.Time
	bufSize      int
	shutdownChan chan bool
	lock         sync.Mutex
}

func NewListenMux(laddr, dest *net.UDPAddr, bufSize int) (*ListenMux, error) {
	conn, err := net.ListenUDP("udp", laddr)
	if err != nil {
		return nil, err
	}
	return &ListenMux{
		listenAddr: laddr,
		listenSock: conn,
		destAddr:   dest,
		workers:    make(map[string]*UDPConnWorker),
		bufSize:    bufSize,
	}, nil
}

func (m *ListenMux) Run() {
	doneChan := make(chan bool)
	go m.GCLoop(doneChan)
	defer func() {
		close(doneChan)
	}()
	for {
		buf := make([]byte, m.bufSize)
		if n, peer, err := m.listenSock.ReadFromUDP(buf); err != nil {
			log.Printf("Error in reading from listen socket: %v", err)
		} else {
			worker, err := m.GetWorker(peer)
			if err != nil {
				log.Printf("Error getting worker: %v", err)
			} else {
				log.Printf("Dispatching %d bytes from %s", n, peer)
				worker.DispatchIncoming(buf[:n])
			}
		}
	}
}

func (m *ListenMux) GCLoop(done <-chan bool) {
	ticker := time.NewTicker(GCInterval)
	for {
		select {
		case <-ticker.C:
			m.gcOnce()
		case <-done:
			return
		}
	}
}

func (m *ListenMux) gcOnce() {
	now := time.Now()
	cleanup := make([]*UDPConnWorker, 0)
	// Inner closure so we can release the lock before shutting down workers
	func() {
		m.mapLock.Lock()
		defer m.mapLock.Unlock()
		for k, v := range m.workers {
			if v.lastActivity.Add(GCDelay).After(now) {
				cleanup = append(cleanup, v)
				delete(m.workers, k)
			}
		}
	}()
	for _, v := range cleanup {
		v.Shutdown()
	}
	if len(cleanup) > 0 {
		log.Printf("Garbage collected %d connections.", len(cleanup))
	}
}

func (m *ListenMux) GetWorker(peer *net.UDPAddr) (*UDPConnWorker, error) {
	key := peer.String()
	m.mapLock.Lock()
	defer m.mapLock.Unlock()
	if rv, ok := m.workers[key]; ok {
		return rv, nil
	}
	rv, err := NewUDPConnWorker(peer, m.destAddr, m.bufSize)
	if err != nil {
		return nil, err
	}
	rv.Start(m.listenSock)
	m.workers[key] = rv
	return rv, nil
}

func NewUDPConnWorker(peer, dest *net.UDPAddr, bufSize int) (*UDPConnWorker, error) {
	conn, err := net.DialUDP("udp", nil, dest)
	if err != nil {
		return nil, err
	}
	rv := &UDPConnWorker{
		peer:         peer,
		dest:         dest,
		conn:         conn,
		incoming:     make(chan []byte, 16),
		responses:    make(chan []byte),
		lastActivity: time.Now(),
		bufSize:      bufSize,
		shutdownChan: make(chan bool),
	}
	return rv, nil
}

func (w *UDPConnWorker) Start(listenSock *net.UDPConn) {
	go w.ClientToDestLoop()
	go w.DestToClientLoop(listenSock)
}

func (w *UDPConnWorker) UpdateLastActivity() {
	w.lock.Lock()
	defer w.lock.Unlock()
	w.lastActivity = time.Now()
}

func (w *UDPConnWorker) DispatchIncoming(dgram []byte) {
	// Not a perfect pattern, but this should work
	if w.incoming != nil {
		w.incoming <- dgram
	}
}

func (w *UDPConnWorker) ClientToDestLoop() {
	w.dgramsToSocket(w.incoming, w.dest, w.conn)
}

func (w *UDPConnWorker) dgramsToSocket(dgrams <-chan []byte, peer *net.UDPAddr, sock *net.UDPConn) {
	w.wg.Add(1)
	defer w.wg.Done()
	for dgram := range dgrams {
		// TODO: reorder/drop
		log.Printf("Sending %d bytes to %s", len(dgram), peer)
		var n int
		var err error
		if sock.RemoteAddr() == nil {
			n, err = sock.WriteTo(dgram, peer)
		} else {
			n, err = sock.Write(dgram)
		}
		if err != nil {
			log.Printf("Error writing on socket: %v", err)
		} else if n != len(dgram) {
			log.Printf("Short write on socket: %d written, %d buffer.", n, len(dgram))
		} else {
			w.UpdateLastActivity()
		}
	}
}

func (w *UDPConnWorker) DestToClientLoop(listenSock *net.UDPConn) {
	w.wg.Add(1)
	defer w.wg.Done()
	defer func() {
		close(w.responses)
	}()
	go w.dgramsToSocket(w.responses, w.peer, listenSock)
	for {
		buf := make([]byte, w.bufSize)
		w.conn.SetReadDeadline(time.Now().Add(ReceiveTimeout))
		n, err := w.conn.Read(buf)
		if err != nil {
			if !errors.Is(err, os.ErrDeadlineExceeded) {
				log.Printf("Error receiving response: %v", err)
			}
		} else {
			// valid packet
			w.responses <- buf[:n]
			w.UpdateLastActivity()
		}
		// Check shutdown
		select {
		case <-w.shutdownChan:
			return
		default:
			continue
		}
	}
}

func (w *UDPConnWorker) Shutdown() {
	incomingChan := w.incoming
	w.incoming = nil
	close(incomingChan)
	w.shutdownChan <- true
	close(w.shutdownChan)
	w.wg.Wait()
}

func main() {
	flag.Parse()

	listenAddr, err := net.ResolveUDPAddr("udp", *listenAddrFlag)
	if err != nil {
		log.Fatalf("Error parsing listen addr: %v", err)
	}

	if *destAddrFlag == "" {
		log.Fatalf("Dest address is required.")
	}

	destAddr, err := net.ResolveUDPAddr("udp", *destAddrFlag)
	if err != nil {
		log.Fatalf("Error parsing dest address: %v", err)
	}

	log.Printf("Starting listen mux on %s to %s", listenAddr, destAddr)
	mux, err := NewListenMux(listenAddr, destAddr, *maxDgramSize)
	if err != nil {
		log.Fatalf("Error starting listener: %v", err)
	}
	mux.Run()
}
