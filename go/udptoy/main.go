package main

import (
	"errors"
	"flag"
	"log"
	insecureRand "math/rand"
	"net"
	"os"
	"os/signal"
	"runtime/pprof"
	"sync"
	"syscall"
	"time"
)

const (
	ReceiveTimeout  = 1 * time.Second
	GCInterval      = 5 * time.Minute
	GCDelay         = 1 * time.Hour
	DefaultBufSize  = 65535
	DefaultMaxDelay = 1 * time.Second
	// Such a high value needed for high rate sending
	IncomingChanCap = 10240
)

var (
	listenAddrFlag = flag.String("listen", "0.0.0.0:9999", "Address on which to listen.")
	destAddrFlag   = flag.String("dest", "", "Destination to which datagrams should be forwarded.")
	maxDgramSize   = flag.Int("maxsize", DefaultBufSize, "Maximum datagram size.")
	dropPctFlag    = flag.Int("drop", 0, "Percent of datagrams to drop.")
	swapPctFlag    = flag.Int("swappy", 0, "Percent odds of datagrams delivered out of order.")
	maxDelayFlag   = flag.Duration("maxdelay", DefaultMaxDelay, "Maximum delay for held packets.")
	cpuProfileFlag = flag.String("cpuprofile", "", "Profile the app")
)

type ListenMuxOption func(*ListenMux) error

type ListenMux struct {
	listenAddr       *net.UDPAddr
	listenSock       *net.UDPConn
	destAddr         *net.UDPAddr
	mapLock          sync.Mutex
	workers          map[string]*UDPConnWorker
	bufSize          int
	maxDelay         time.Duration
	dropPct          float32
	swapPct          float32
	totalListenBytes int64
	clientBytesIn    int64 // from client
	clientBytesOut   int64 // to client
	destBytesIn      int64 // from dest
	destBytesOut     int64 // to dest
	doneChan         chan bool
}

type UDPConnWorker struct {
	peer           *net.UDPAddr
	dest           *net.UDPAddr
	conn           *net.UDPConn
	incoming       chan []byte
	responses      chan []byte
	wg             sync.WaitGroup
	lastActivity   time.Time
	bufSize        int
	shutdownChan   chan bool
	lock           sync.Mutex
	maxDelay       time.Duration
	dropPct        float32
	swapPct        float32
	clientBytesIn  int64 // from client
	clientBytesOut int64 // to client
	destBytesIn    int64 // from dest
	destBytesOut   int64 // to dest
}

func NewListenMux(laddr, dest *net.UDPAddr, opts ...ListenMuxOption) (*ListenMux, error) {
	conn, err := net.ListenUDP("udp", laddr)
	if err != nil {
		return nil, err
	}
	if err := conn.SetReadBuffer(256 * 1024); err != nil {
		conn.Close()
		return nil, err
	}
	rv := &ListenMux{
		listenAddr: laddr,
		listenSock: conn,
		destAddr:   dest,
		workers:    make(map[string]*UDPConnWorker),
		bufSize:    DefaultBufSize,
		maxDelay:   DefaultMaxDelay,
		doneChan:   make(chan bool, 1),
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
		log.Printf("Mux exiting")
	}()
	for {
		buf := make([]byte, m.bufSize)
		// TODO: add timeout support
		if n, peer, err := m.listenSock.ReadFromUDP(buf); err != nil {
			if !errors.Is(err, net.ErrClosed) {
				log.Printf("Error in reading from listen socket: %v", err)
			}
		} else {
			worker, err := m.GetWorker(peer)
			if err != nil {
				log.Printf("Error getting worker: %v", err)
			} else {
				m.totalListenBytes += int64(n)
				//log.Printf("Dispatching %d bytes from %s", n, peer)
				worker.DispatchIncoming(buf[:n])
			}
		}
		select {
		case <-m.doneChan:
			return
		default:
			continue
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
		m.clientBytesIn += v.clientBytesIn
		m.clientBytesOut += v.clientBytesOut
		m.destBytesIn += v.destBytesIn
		m.destBytesOut += v.destBytesOut
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

func (m *ListenMux) Shutdown() {
	m.mapLock.Lock()
	defer m.mapLock.Unlock()
	close(m.doneChan)
	m.listenSock.Close()
	for k, v := range m.workers {
		v.Shutdown()
		m.clientBytesIn += v.clientBytesIn
		m.clientBytesOut += v.clientBytesOut
		m.destBytesIn += v.destBytesIn
		m.destBytesOut += v.destBytesOut
		delete(m.workers, k)
	}
}

func (m *ListenMux) LogStats() {
	m.mapLock.Lock()
	defer m.mapLock.Unlock()
	for _, v := range m.workers {
		v.LogStats()
	}
	log.Printf("Parent: C->D: %d/%d, D->C: %d/%d", m.clientBytesIn, m.destBytesOut, m.destBytesIn, m.clientBytesOut)
	log.Printf("Listen bytes received: %d", m.totalListenBytes)
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
		incoming:     make(chan []byte, IncomingChanCap),
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
	} else {
		log.Printf("BUG: attempt to write on nil channel!")
	}
}

func (w *UDPConnWorker) ClientToDestLoop() {
	w.dgramsToSocket(w.incoming, w.dest, w.conn, &w.clientBytesIn, &w.destBytesOut)
}

func (w *UDPConnWorker) dgramsToSocket(dgrams <-chan []byte, peer *net.UDPAddr, sock *net.UDPConn, bytesIn, bytesOut *int64) {
	w.wg.Add(1)
	shuffler := make([][]byte, 0)
	ticker := time.NewTicker(w.maxDelay)
	flush := func() {
		if len(shuffler) == 0 {
			return
		}
		for _, n := range insecureRand.Perm(len(shuffler)) {
			w.sendDgram(shuffler[n], peer, sock, bytesOut)
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
			*bytesIn += int64(len(dgram))
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
			w.sendDgram(dgram, peer, sock, bytesOut)
			flush()
		case <-ticker.C:
			// timeout, send and clear buffer
			flush()
		}
	}
}

func (w *UDPConnWorker) sendDgram(dgram []byte, peer *net.UDPAddr, sock *net.UDPConn, counter *int64) {
	//log.Printf("Sending %d bytes to %s", len(dgram), peer)
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
		*counter += int64(n)
		log.Printf("Short write on socket: %d written, %d buffer.", n, len(dgram))
	} else {
		*counter += int64(n)
		w.UpdateLastActivity()
	}
}

func (w *UDPConnWorker) DestToClientLoop(listenSock *net.UDPConn) {
	w.wg.Add(1)
	defer w.wg.Done()
	defer func() {
		close(w.responses)
	}()
	go w.dgramsToSocket(w.responses, w.peer, listenSock, &w.destBytesIn, &w.clientBytesOut)
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

func (w *UDPConnWorker) LogStats() {
	log.Printf("%s: C->D: %d/%d, D->C: %d/%d", w.peer.String(), w.clientBytesIn, w.destBytesOut, w.destBytesIn, w.clientBytesOut)
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

	if *cpuProfileFlag != "" {
		f, err := os.Create(*cpuProfileFlag)
		if err != nil {
			log.Fatal(err)
		}
		if err := pprof.StartCPUProfile(f); err != nil {
			log.Fatal(err)
		}
		defer func() {
			log.Printf("Stopping profiling.")
			pprof.StopCPUProfile()
			f.Close()
		}()
	}

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

	sigChan := make(chan os.Signal, 1)
	doneChan := make(chan bool, 1)
	signal.Notify(sigChan, syscall.SIGTERM, syscall.SIGINT, syscall.SIGUSR1)
	// Signal handler
	go func() {
		defer close(doneChan)
		for sig := range sigChan {
			switch sig {
			case syscall.SIGINT, syscall.SIGTERM:
				log.Printf("%v received, shutting down.", sig)
				mux.Shutdown()
				mux.LogStats()
				return
			case syscall.SIGUSR1:
				mux.LogStats()
			default:
				log.Printf("Unknown signal %v received, ignoring!", sig)
			}
		}
	}()

	mux.Run()
	log.Printf("Post mux!")
	<-doneChan
	log.Printf("Done!")
}
