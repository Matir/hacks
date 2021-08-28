package main

import (
	"bytes"
	"net"
)

type ConnLogger struct {
	net.Conn
	lineBuf  []byte
	lineDone bool
}

func (cl *ConnLogger) GetFirstLine() []byte {
	if cl.lineBuf == nil {
		return nil
	}
	if p := bytes.IndexByte(cl.lineBuf, byte('\n')); p >= 0 {
		return cl.lineBuf[:p+1]
	}
	return cl.lineBuf
}

func (cl *ConnLogger) Read(b []byte) (int, error) {
	n, err := cl.Conn.Read(b)
	if err != nil {
		return n, err
	}
	if !cl.lineDone {
		cl.lineBuf = append(cl.lineBuf, b[:n]...)
		cl.lineDone = bytes.IndexByte(cl.lineBuf, byte('\n')) > -1
	}
	return n, nil
}
