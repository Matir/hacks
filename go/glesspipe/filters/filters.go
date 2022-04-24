package filters

type FilterScore int

const (
	FilterScoreNoMatch FilterScore = iota
	FilterScoreWeakMatch
	FilterScoreFullMatch
)
