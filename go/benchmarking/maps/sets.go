package main

type IntBoolSet map[int]bool

func (ibs IntBoolSet) Add(v int) {
	ibs[v] = true
}

func (ibs IntBoolSet) Contains(v int) bool {
	_, ok := ibs[v]
	return ok
}

type IntIntSet map[int]interface{}

func (iis IntIntSet) Add(v int) {
	iis[v] = nil
}

func (iis IntIntSet) Contains(v int) bool {
	_, ok := iis[v]
	return ok
}

type StringBoolSet map[string]bool

func (sbs StringBoolSet) Add(v string) {
	sbs[v] = true
}

func (sbs StringBoolSet) Contains(v string) bool {
	_, ok := sbs[v]
	return ok
}

type StringIntSet map[string]interface{}

func (sis StringIntSet) Add(v string) {
	sis[v] = true
}

func (sis StringIntSet) Contains(v string) bool {
	_, ok := sis[v]
	return ok
}
