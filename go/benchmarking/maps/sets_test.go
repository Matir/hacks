package main

import (
	"testing"
)

func TestIntBoolSet(t *testing.T) {
	s := make(IntBoolSet)
	s.Add(1)
	s.Add(3)
	if !s.Contains(1) {
		t.Fatal("Expected 1.")
	}
	if s.Contains(4) {
		t.Fatal("Did not expect 4.")
	}
}

func BenchmarkIntBoolSet(b *testing.B) {
	s := make(IntBoolSet)
	for i := 0; i < b.N; i++ {
		s.Add(i)
	}
	for i := 0; i < b.N; i++ {
		s.Contains(i * 2)
	}
}

func BenchmarkIntIntSet(b *testing.B) {
	s := make(IntIntSet)
	for i := 0; i < b.N; i++ {
		s.Add(i)
	}
	for i := 0; i < b.N; i++ {
		s.Contains(i * 2)
	}
}
