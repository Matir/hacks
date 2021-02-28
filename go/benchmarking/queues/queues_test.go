package main

import (
	"container/list"
	"testing"
)

func BenchmarkSliceQueue(b *testing.B) {
	q := make([]int, 100)
	for i := range q {
		q[i] = i
	}
	b.ReportAllocs()
	for l := 0; l < b.N; l++ {
		for i := 0; i < 100000; i++ {
			q = append(q, i)
			q = q[1:]
		}
	}
}

func BenchmarkListQueue(b *testing.B) {
	q := list.New()
	for i := 0; i < 100; i++ {
		q.PushBack(i)
	}
	b.ReportAllocs()
	for l := 0; l < b.N; l++ {
		for i := 0; i < 100000; i++ {
			q.PushBack(i)
			q.Remove(q.Front())
		}
	}
}

func BenchmarkFixedQueue(b *testing.B) {
	q := NewFixedQueue(100)
	for i := 0; i < 100; i++ {
		q.Push(i)
	}
	b.ReportAllocs()
	for l := 0; l < b.N; l++ {
		for i := 0; i < 100000; i++ {
			q.Pop()
			q.Push(i)
		}
	}
}
