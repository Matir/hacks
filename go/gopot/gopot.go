package main

import (
	"crypto/rand"
	"crypto/rsa"
	"errors"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"golang.org/x/crypto/ssh"
	"upper.io/db.v3"
	"upper.io/db.v3/lib/sqlbuilder"
	"upper.io/db.v3/sqlite"
)

type Result struct {
	Username   string    `db:"username"`
	Password   string    `db:"password"`
	Timestamp  time.Time `db:"timestamp"`
	RemoteIP   string    `db:"remote_ip"`
	RemotePort int       `db:"remote_port"`
	Client     string    `db:"client"`
}

const (
	tblResults = "results"
)

var (
	ErrorBadPassword = errors.New("Invalid username or password.")
	flagListenSpec   = flag.String("listen", ":2222", "IP:port to listen on.")
	flagDBPath       = flag.String("dbpath", "gopot.db", "Database path.")
)

func BuildPasswordHandler(ch chan<- Result) func(ssh.ConnMetadata, []byte) (*ssh.Permissions, error) {
	return func(conn ssh.ConnMetadata, pw []byte) (*ssh.Permissions, error) {
		host, port, err := net.SplitHostPort(conn.RemoteAddr().String())
		if err != nil {
			log.Printf("Error getting hostport: %s %s", conn.RemoteAddr().String(), err)
			host = conn.RemoteAddr().String()
		}
		portno, err := strconv.Atoi(port)
		if err != nil {
			portno = 0
		}
		ch <- Result{
			Username:   conn.User(),
			Password:   string(pw),
			Timestamp:  time.Now(),
			Client:     string(conn.ClientVersion()),
			RemoteIP:   host,
			RemotePort: portno,
		}
		return nil, ErrorBadPassword
	}
}

func BuildSSHServerConfig(ch chan<- Result) *ssh.ServerConfig {
	cfg := &ssh.ServerConfig{
		MaxAuthTries:     3,
		PasswordCallback: BuildPasswordHandler(ch),
	}
	// TODO: use on-disk keys to reduce startup time?
	log.Printf("Generating new 2048-bit RSA key.")
	privKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		log.Fatalf("Error generating private key: %s", err)
	}
	log.Printf("Done generating key.")
	signer, err := ssh.NewSignerFromKey(privKey)
	if err != nil {
		log.Fatalf("Error setting up signer: %s", err)
	}
	cfg.AddHostKey(signer)
	return cfg
}

func ResultWorker(dbConn db.Database, ch <-chan Result, doneCh chan<- bool) {
	log.Printf("ResultWorker starting...")
	defer log.Printf("ResultWorker exiting...")
	defer func() { doneCh <- true }()
	for e := range ch {
		ResultHandler(dbConn, e)
	}
}

func ResultHandler(dbConn db.Database, r Result) {
	log.Printf("Connection from %15s: Username: %12s Password: %12s", r.RemoteIP, r.Username, r.Password)
	if _, err := dbConn.Collection(tblResults).Insert(r); err != nil {
		log.Printf("Error inserting to database: %s", err)
	}
}

func ServerWorker(sock net.Listener, cfg *ssh.ServerConfig, shut <-chan bool) {
	log.Printf("ServerWorker starting...")
	defer log.Printf("ServerWorker exiting...")
	for {
		select {
		case <-shut:
			return
		default:
		}
		conn, err := sock.Accept()
		if err != nil {
			log.Printf("Error in accept: %s", err)
		}
		if err := conn.SetDeadline(time.Now().Add(time.Minute)); err != nil {
			log.Printf("Error in SetDeadline: %s", err)
		}
		go func() {
			// TODO: consider storing in DB?
			log.Printf("Accepted connection from %s", conn.RemoteAddr().String())
			sshConn, _, _, _ := ssh.NewServerConn(conn, cfg)
			if sshConn != nil {
				sshConn.Close()
			}
		}()
	}
}

// Get the DB connection
func GetDatabase(path string) (sqlbuilder.Database, error) {
	if settings, err := sqlite.ParseURL("file://" + path); err != nil {
		return nil, err
	} else {
		return sqlite.Open(settings)
	}
}

// Check if we have tables
func SetupDatabase(conn sqlbuilder.Database) error {
	resTbl := conn.Collection(tblResults)
	if !resTbl.Exists() {
		// Query builder does not support CREATE statements
		query := "CREATE TABLE %s (" +
			"username TEXT, " +
			"password TEXT, " +
			"timestamp TEXT, " +
			"remote_ip TEXT, " +
			"remote_port INTEGER, " +
			"client TEXT)"
		_, err := conn.Exec(fmt.Sprintf(query, tblResults))
		if err != nil {
			log.Printf("Error creating database table: %s", err)
			return err
		}
	}
	return nil
}

func main() {
	// Parse flags
	flag.Parse()

	// Setup DB
	dbConn, err := GetDatabase(*flagDBPath)
	if err != nil {
		log.Fatalf("Error getting database: %s", err)
	}
	if err := SetupDatabase(dbConn); err != nil {
		log.Fatalf("Error setting up database: %s", err)
	}

	// Setup result handler
	resultChan := make(chan Result, 10)
	doneChan := make(chan bool)
	cfg := BuildSSHServerConfig(resultChan)
	go ResultWorker(dbConn, resultChan, doneChan)

	// Startup listener
	listener, err := net.Listen("tcp", *flagListenSpec)
	if err != nil {
		log.Fatalf("Error listening: %s", err)
	}

	// Handle CTRL+C
	shutChan := make(chan bool, 1)
	sigChan := make(chan os.Signal, 2)
	go func() {
		<-sigChan
		log.Printf("Starting shutdown....")
		shutChan <- true
		listener.Close()
		log.Printf("Listener closed.")
	}()
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Start main worker
	ServerWorker(listener, cfg, shutChan)

	// Shutting down here
	close(resultChan)
	<-doneChan
	log.Printf("Shut down normally")
	os.Exit(0)
}

func init() {
	log.SetFlags(log.LstdFlags | log.LUTC | log.Lshortfile)
}
