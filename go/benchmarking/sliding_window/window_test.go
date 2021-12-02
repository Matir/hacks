package main

import (
	"math/rand"
	"testing"
)

var testdata = GenerateData()

const WindowSize = 5

type SlidingWindow struct {
	window []int
	offset int
}

func SliceSum(d []int) int {
	total := 0
	for _, v := range d {
		total += v
	}
	return total
}

func GenerateData() []int {
	rv := make([]int, 4096)
	for i := range rv {
		rv[i] = rand.Intn(1 << 16)
	}
	return rv
}

func (sw SlidingWindow) Add(n int) {
	sw.window[sw.offset] = n
	sw.offset++
	if sw.offset > len(sw.window) {
		sw.offset = 0
	}
}

func (sw SlidingWindow) Sum() int {
	return SliceSum(sw.window)
}

func BenchmarkWindow_Slice(b *testing.B) {
	for i := 0; i < b.N; i++ {
		win := make([]int, WindowSize)
		for _, n := range testdata {
			win = append(win, n)[len(win)-WindowSize:]
			SliceSum(win)
		}
	}
}

func BenchmarkWindow_Struct(b *testing.B) {
	for i := 0; i < b.N; i++ {
		win := SlidingWindow{
			window: make([]int, WindowSize),
		}
		for _, n := range testdata {
			win.Add(n)
			win.Sum()
		}
	}
}
