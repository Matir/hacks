package main

import (
	"fmt"
	"math"
	"math/rand"
	"time"
)

const (
	INTERVAL_MILLIS = 200
)

func ch1Voltage(n int) int {
	return 12000 + rand.Intn(n%50+1)
}

func ch1Amps(n int) int {
	return 1337 + rand.Intn(n%10+1) + n%1000
}

func ch2Voltage(n int) int {
	return 5000 + int(100*math.Sin(float64(n)/100))
}

func ch2Amps(n int) int {
	return 1000 + int(100*math.Sin(float64(n)/100))
}

func ch3Voltage(n int) int {
	return 1500
}

func ch3Amps(n int) int {
	return 0
}

func doLine(n int) {
	fmt.Printf("%05d|%05d|%05d|%05d|%05d|%05d|%05d|\n",
		n,
		ch1Voltage(n),
		ch1Amps(n),
		ch2Voltage(n),
		ch2Amps(n),
		ch3Voltage(n),
		ch3Amps(n))
}

func main() {
	tick := time.NewTicker(INTERVAL_MILLIS * time.Millisecond)
	i := 0
	defer tick.Stop()
	for _ = range tick.C {
		doLine(i)
		i++
	}
}
