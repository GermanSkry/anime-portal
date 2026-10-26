package services

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"time"
)

type SerpAPIClient struct {
	apiKey string
	client *http.Client
}

type SerpAPIResponse struct {
	OrganicResults []struct {
		Title   string `json:"title"`
		Link    string `json:"link"`
		Snippet string `json:"snippet"`
	} `json:"organic_results"`
}

type SearchResult struct {
	Title   string `json:"title"`
	URL     string `json:"url"`
	Snippet string `json:"snippet"`
}

func NewSerpAPIClient() *SerpAPIClient {
	return &SerpAPIClient{
		apiKey: os.Getenv("SERPAPI_KEY"),
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// Search performs a web search via SerpAPI
func (c *SerpAPIClient) Search(query string, limit int) ([]SearchResult, error) {
	if c.apiKey == "" {
		return []SearchResult{}, fmt.Errorf("SERPAPI_KEY not set")
	}

	params := url.Values{
		"q":       {query},
		"engine":  {"google"},
		"api_key": {c.apiKey},
		"num":     {fmt.Sprintf("%d", limit)},
		"gl":      {"us"},
	}

	req, err := http.NewRequest("GET", "https://serpapi.com/search?"+params.Encode(), nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", "anime-search-service/1.0")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("SerpAPI error: %d - %s", resp.StatusCode, string(body))
	}

	var apiResp SerpAPIResponse
	if err := json.NewDecoder(resp.Body).Decode(&apiResp); err != nil {
		return nil, err
	}

	results := []SearchResult{}
	for _, item := range apiResp.OrganicResults {
		if len(results) >= limit {
			break
		}
		results = append(results, SearchResult{
			Title:   item.Title,
			URL:     item.Link,
			Snippet: item.Snippet,
		})
	}

	return results, nil
}

// SearchAnime performs an anime-specific search
func (c *SerpAPIClient) SearchAnime(query string) ([]SearchResult, error) {
	searchQuery := fmt.Sprintf("%s anime 2026", query)
	return c.Search(searchQuery, 3)
}

// SearchTrending searches for trending anime
func (c *SerpAPIClient) SearchTrending() ([]SearchResult, error) {
	return c.Search("trending anime 2026 myanimelist", 5)
}
