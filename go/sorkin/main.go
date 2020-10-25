package main

import (
	"encoding/json"
	"fmt"
	"golang.org/x/net/html"
	"net/http"
	"strings"
	"github.com/andybalholm/cascadia"
	"io"
	"os"
)


const (
	SHOW_PATTERN = "https://www.imdb.com/title/%s/"
	SEASON_PATTERN = "https://www.imdb.com/title/%s/episodes?season=%d"
	CREDITS_PATTERN = "https://www.imdb.com/title/%s/fullcredits"
)

var (
	DivInfoSel cascadia.Sel
	ASel cascadia.Sel
	CastRowSel cascadia.Sel
	TDSel cascadia.Sel
)

type Show struct {
	Name       string
	ID         string
	NumSeasons int
	Seasons    []*Season
}

type Season struct {
	Show      *Show `json:"-"`
	SeasonNum int
	Episodes  []*Episode
}

type Episode struct {
	Season     *Season `json:"-"`
	Title      string
	EpisodeNum int
	EpId string
	Cast       []*CastMember
}

type CastMember struct {
	Actor   string
	ActorID string
	Role    string
}

func (s *Show) GetURL() string {
	return fmt.Sprintf(SHOW_PATTERN, s.ID)
}

func (s *Show) GetNumSeasons() (int, error) {
	resp, err := http.Get(s.GetURL())
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return 0, fmt.Errorf("Unexpected response code: %d", resp.StatusCode)
	}
	root, err := html.Parse(resp.Body)
	if err != nil {
		return 0, err
	}
	var searcher func(*html.Node) (int, bool)
	searcher = func(n *html.Node) (int, bool) {
		if isDivClass(n, "seasons-and-year-nav") {
			numSeasons := 0
			for c := n.FirstChild; c != nil; c = c.NextSibling {
				if c.Data == "div" {
					for e := c.FirstChild; e != nil; e = e.NextSibling {
						if isSeasonLink(e) {
							numSeasons++
						}
					}
				}
			}
			return numSeasons, true
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			if n, ok := searcher(c); ok {
				return n, ok
			}
		}
		return 0, false
	}
	if n, ok := searcher(root); ok {
		s.NumSeasons = n
		return n, nil
	}
	return 0, fmt.Errorf("Could not find seasons")
}

func (s *Show) LoadSeasons() error {
	if s.NumSeasons == 0 {
		if _, err := s.GetNumSeasons(); err != nil {
			return err
		}
	}
	for i := 1; i<=s.NumSeasons ; i++ {
		fmt.Printf("Loading %s season %d\n", s.Name, i)
		season := &Season{
			Show: s,
			SeasonNum: i,
		}
		s.Seasons = append(s.Seasons, season)
		if err := season.LoadEpisodes(); err != nil {
			return err
		}
	}
	return nil
}

func (s *Season) GetURL() string {
	return fmt.Sprintf(SEASON_PATTERN, s.Show.ID, s.SeasonNum)
}

func (s *Season) LoadEpisodes() error {
	resp, err := http.Get(s.GetURL())
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("Unexpected response code: %d", resp.StatusCode)
	}
	root, err := html.Parse(resp.Body)
	if err != nil {
		return err
	}
	for i, epinfo := range cascadia.QueryAll(root, DivInfoSel) {
		episode := &Episode{
			Season: s,
			EpisodeNum: i+1,
		}
		s.Episodes = append(s.Episodes, episode)
		eplink := cascadia.Query(epinfo, ASel)
		if eplink == nil {
			return fmt.Errorf("Unable to find episode link!")
		}
		if title, epid, err := parseEpisodeLink(eplink); err != nil {
			return err
		} else {
			episode.Title = title
			episode.EpId = epid
		}
		if err := episode.LoadCast(); err != nil {
			return err
		}
	}
	return nil
}

func (e *Episode) GetURL() string {
	return fmt.Sprintf(CREDITS_PATTERN, e.EpId)
}

func (e *Episode) LoadCast() error {
	resp, err := http.Get(e.GetURL())
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("Unexpected response code: %d", resp.StatusCode)
	}
	root, err := html.Parse(resp.Body)
	for _, castrow := range cascadia.QueryAll(root, CastRowSel) {
		cm := parseCastRow(castrow)
		if cm != nil {
			e.Cast = append(e.Cast, cm)
		}
	}
	return nil
}

func parseCastRow(n *html.Node) *CastMember {
	cells := cascadia.QueryAll(n, TDSel)
	if len(cells) != 4 {
		return nil
	}
	cm := &CastMember{}
	actorNode := cells[1]
	for child := actorNode.FirstChild; child != nil; child=child.NextSibling {
		if child.Data == "a" {
			actorNode = child
			break
		}
	}
	cm.Actor = getTextContent(actorNode)
	for _, attr := range actorNode.Attr {
		if attr.Key == "href" {
			pieces := strings.Split(attr.Val, "/")
			if len(pieces) >= 3 {
				cm.ActorID = pieces[2]
			}
			break
		}
	}
	roleNode := cells[3]
	for child := roleNode.FirstChild; child != nil; child=child.NextSibling {
		if child.Data == "a" {
			roleNode = child
			break
		}
	}
	cm.Role = getTextContent(roleNode)
	return cm
}

func getTextContent(n *html.Node) string {
	for {
		if n == nil {
			return ""
		}
		if n.Type == html.TextNode {
			return strings.TrimSpace(n.Data)
		}
		n = n.FirstChild
	}
}

// Extract the name of the episode and the IMDB EpId
func parseEpisodeLink(n *html.Node) (string, string, error) {
	chld := n.FirstChild
	if chld.Type != html.TextNode {
		return "", "", fmt.Errorf("No child text node")
	}
	title := chld.Data
	var alink string
	for _, attr := range n.Attr {
		if attr.Key == "href" {
			alink = attr.Val
			break
		}
	}
	if alink == "" {
		return "", "", fmt.Errorf("Unable to find link")
	}
	pieces := strings.Split(alink, "/")
	if len(pieces) < 3 {
		return "", "", fmt.Errorf("Unable to find epid")
	}
	return title, pieces[2], nil
}

func isSeasonLink(n *html.Node) bool {
	if n.Data == "a" {
		for _, a := range n.Attr {
			if a.Key == "href" && strings.Contains(a.Val, "episodes?season") {
				return true
			}
		}
	}
	return false
}

// Check for DIV with Class
func isDivClass(n *html.Node, c string) bool {
	if n.Type == html.ElementNode && n.Data == "div" {
		for _, a := range n.Attr {
			if a.Key == "class" && a.Val == c {
				return true
			}
		}
	}
	return false
}

var Shows = []*Show{
	&Show{
		Name: "The West Wing",
		ID:   "tt0200276",
	},
	&Show{
		Name: "Sports Night",
		ID:   "tt0165961",
	},
}

func DumpShows(w io.Writer, shows []*Show) error {
	enc := json.NewEncoder(w)
	enc.SetIndent("", "    ")
	return enc.Encode(shows)
}

func demo() {
	for _, s := range Shows {
		_, err := s.GetNumSeasons()
		if err != nil {
			fmt.Printf("Error getting season data: %s\n", err)
			continue
		}
		fmt.Printf("%s has %d seasons.\n", s.Name, s.NumSeasons)
		if err := s.LoadSeasons(); err != nil {
			fmt.Printf("Error loading seasons: %s\n", err)
		}
	}
	DumpShows(os.Stdout, Shows)
	if fp, err := os.Create("sorkin.json"); err != nil {
		fmt.Printf("Error saving output: %s\n", err)
	} else {
		defer fp.Close()
		DumpShows(fp, Shows)
	}
}

func main() {
	demo()
}

func init() {
	mustParse := func(sel string) cascadia.Sel {
		if a, err := cascadia.Parse(sel); err != nil {
			panic(err)
		} else {
			return a
		}
	}
	ASel = mustParse("a")
	DivInfoSel = mustParse("div.info")
	CastRowSel = mustParse("table.cast_list tr")
	TDSel = mustParse("td")
}
