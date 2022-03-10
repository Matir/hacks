package main

import (
	"errors"
	"flag"
	"log"
	insecureRand "math/rand"
	"net"
	"os"
	"sync"
	"time"
)

const (
	ReceiveTimeout  = 1 * time.Second
	GCInterval      = 5 * time.Minute
	GCDelay         = 1 * time.Hour
	DefaultBufSize  = 65535
	DefaultMaxDelay = 1 * time.Second
)

var (
	listenAddrFlag = flag.String("listen", "0.0.0.0:9999", "Address on which to listen.")
	destAddrFlag   = flag.String("dest", "", "Destination to which datagrams should be forwarded.")
	maxDgramSize   = flag.Int("maxsize", DefaultBufSize, "Maximum datagram size.")
	dropPctFlag    = flag.Int("drop", 0, "Percent of datagrams to drop.")
	swapPctFlag    = flag.Int("swappy", 0, "Percent odds of datagrams delivered out of order.")
	maxDelayFlag   = flag.Duration("maxdelay", DefaultMaxDelay, "Maximum delay for held packets.")
)

type ListenMuxOption func(*ListenMux) error

type ListenMux struct {
	listenAddr *net.UDPAddr
	listenSock *net.UDPConn
	destAddr   *net.UDPAddr
	mapLock    sync.Mutex
	workers    map[string]*UDPConnWorker
	bufSize    int
	maxDelay   time.Duration
	dropPct    float32
	swapPct    float32
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
	maxDelay     time.Duration
	dropPct      float32
	swapPct      float32
}

func NewListenMux(laddr, dest *net.UDPAddr, opts ...ListenMuxOption) (*ListenMux, error) {
	conn, err := net.ListenUDP("udp", laddr)
	if err != nil {
		return nil, err
	}
	rv := &ListenMux{
		listenAddr: laddr,
		listenSock: conn,
		destAddr:   dest,
		workers:    make(map[string]*UDPConnWorker),
		bufSize:    DefaultBufSize,
		maxDelay:   DefaultMaxDelay,
	}
	for _, opt := range opts {
		if err := opt(rv); err != nil {
			return nil, err
		}
	}
	return rv, nil
}

func WithBufSize(bufSize int) ListenMuxOption {
	return func(mux *ListenMux) error {
		if bufSize < 1 || bufSize > 65535 {
			return errors.New("Buf size must be 1-65535")
		}
		mux.bufSize = bufSize
		return nil
	}
}

func WithMaxDelay(delay time.Duration) ListenMuxOption {
	return func(mux *ListenMux) error {
		mux.maxDelay = delay
		return nil
	}
}

func WithDropPercent(dropPct float32) ListenMuxOption {
	return func(mux *ListenMux) error {
		if err := validatePercentage(dropPct); err != nil {
			return err
		}
		mux.dropPct = dropPct
		return nil
	}
}

func WithSwapPercent(swapPct float32) ListenMuxOption {
	return func(mux *ListenMux) error {
		if err := validatePercentage(swapPct); err != nil {
			return err
		}
		mux.swapPct = swapPct
		return nil
	}
}

func validatePercentage(pct float32) error {
	if pct < 0.0 || pct > 1.0 {
		return errors.New("Percentage must be 0.0-1.0")
	}
	return nil
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
	defer ticker.Stop()
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
	rv, err := NewUDPConnWorker(peer, m.destAddr)
	if err != nil {
		return nil, err
	}
	// TODO: should this copying be done elsewhere?
	rv.bufSize = m.bufSize
	rv.dropPct = m.dropPct
	rv.swapPct = m.swapPct
	rv.maxDelay = m.maxDelay
	rv.Start(m.listenSock)
	m.workers[key] = rv
	return rv, nil
}

func NewUDPConnWorker(peer, dest *net.UDPAddr) (*UDPConnWorker, error) {
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
		bufSize:      DefaultBufSize,
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
	shuffler := make([][]byte, 0)
	ticker := time.NewTicker(w.maxDelay)
	flush := func() {
		if len(shuffler) == 0 {
			return
		}
		for _, n := range insecureRand.Perm(len(shuffler)) {
			w.sendDgram(shuffler[n], peer, sock)
		}
		shuffler = shuffler[:0]
	}
	defer func() {
		ticker.Stop()
		flush()
		w.wg.Done()
	}()
	for {
		select {
		case dgram, ok := <-dgrams:
			if !ok {
				// closed channel
				return
			}
			// Handle swapping/shuffling
			if RandPercentCheck(w.dropPct) {
				log.Printf("Dropping %d bytes", len(dgram))
				continue
			}
			if RandPercentCheck(w.swapPct) {
				log.Printf("Storing %d bytes for swapping", len(dgram))
				// store
				shuffler = append(shuffler, dgram)
				ticker.Reset(w.maxDelay)
				continue
			}
			w.sendDgram(dgram, peer, sock)
			flush()
		case <-ticker.C:
			// timeout, send and clear buffer
			flush()
		}
	}
}

func (w *UDPConnWorker) sendDgram(dgram []byte, peer *net.UDPAddr, sock *net.UDPConn) {
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

// Returns true approximately pct of the time.
func RandPercentCheck(pct float32) bool {
	// special case edges for floating point error
	if pct < 0.0001 {
		return false
	}
	if pct > 0.9999 {
		return true
	}
	return insecureRand.Float32() <= pct
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

	opts := []ListenMuxOption{
		WithBufSize(*maxDgramSize),
		WithMaxDelay(*maxDelayFlag),
	}

	if *dropPctFlag != 0 {
		if *dropPctFlag < 0 || *dropPctFlag > 100 {
			log.Fatalf("Drop percent must be 0-100, not %d", *dropPctFlag)
		}
		opts = append(opts, WithDropPercent(float32(*dropPctFlag)/100))
	}

	if *swapPctFlag != 0 {
		if *swapPctFlag < 0 || *swapPctFlag > 100 {
			log.Fatalf("Swap percent must be 0-100, not %d", *swapPctFlag)
		}
		opts = append(opts, WithSwapPercent(float32(*swapPctFlag)/100))
	}

	log.Printf("Starting listen mux on %s to %s", listenAddr, destAddr)
	mux, err := NewListenMux(listenAddr, destAddr, opts...)
	if err != nil {
		log.Fatalf("Error starting listener: %v", err)
	}
	mux.Run()
}
