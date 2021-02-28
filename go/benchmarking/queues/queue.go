package main

type FixedQueue struct {
	data  []int
	start int
	end   int
}

func (q *FixedQueue) Push(n int) {
	q.data[q.end] = n
	if q.end == q.start {
		q.start = (q.start + 1) % len(q.data)
	}
	q.end = (q.end + 1) % len(q.data)
}

func (q *FixedQueue) Pop() int {
	rv := q.data[q.start]
	if q.start != q.end {
		q.start = (q.start + 1) % len(q.data)
	}
	return rv
}

func NewFixedQueue(l int) *FixedQueue {
	return &FixedQueue{
		data:  make([]int, l),
		start: 0,
		end:   0,
	}
}
