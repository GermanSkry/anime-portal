package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"anime-search-service/cache"
	"anime-search-service/db"
	"anime-search-service/services"

	"github.com/getsentry/sentry-go"
	"github.com/gin-gonic/gin"
)

type SearchHandlers struct {
	cache    *cache.RedisCache
	db       *db.Connection
	serpapi  *services.SerpAPIClient
	analytics *services.PostHogClient
}

type SearchRequest struct {
	Query string `json:"query" binding:"required"`
}

type ConcurrentSearchRequest struct {
	Query string `json:"query" binding:"required"`
}

type ConcurrentSearchResult struct {
	Web   []services.SearchResult `json:"web"`
	Anime []map[string]interface{} `json:"anime"`
}

func NewSearchHandlers(redisClient *cache.RedisCache, dbConn *db.Connection) *SearchHandlers {
	return &SearchHandlers{
		cache:     redisClient,
		db:        dbConn,
		serpapi:   services.NewSerpAPIClient(),
		analytics: services.NewPostHogClient(),
	}
}

// SearchWeb searches the web with caching
func (sh *SearchHandlers) SearchWeb(c *gin.Context) {
	var req SearchRequest
	if err := c.BindJSON(&req); err != nil {
		sentry.CaptureException(err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	startTime := time.Now()
	cacheKey := fmt.Sprintf("web_search:%s", req.Query)

	// Check cache first
	var results []services.SearchResult
	if err := sh.cache.Get(ctx, cacheKey, &results); err == nil {
		sh.analytics.TrackCacheHit(req.Query)
		sh.db.LogSearch(req.Query, len(results), "web_cached")
		c.JSON(http.StatusOK, results)
		return
	}

	// Cache miss - fetch from SerpAPI
	sh.analytics.TrackCacheMiss(req.Query)

	results, err := sh.serpapi.Search(req.Query, 3)
	if err != nil {
		sentry.CaptureException(err)
		sh.analytics.TrackAPICall("serpapi", false, time.Since(startTime))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to search web"})
		return
	}

	// Store in cache for 1 hour
	sh.cache.Set(ctx, cacheKey, results, 1*time.Hour)
	sh.analytics.TrackAPICall("serpapi", true, time.Since(startTime))
	sh.analytics.TrackSearch(req.Query, len(results), "web", time.Since(startTime))
	sh.db.LogSearch(req.Query, len(results), "web")

	c.JSON(http.StatusOK, results)
}

// SearchAnime calls the Python FastAPI anime endpoint
func (sh *SearchHandlers) SearchAnime(c *gin.Context) {
	var req SearchRequest
	if err := c.BindJSON(&req); err != nil {
		sentry.CaptureException(err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Call Python FastAPI backend
	pythonURL := "http://localhost:8000/api/search/semantic?query_text=" + req.Query + "&limit=3"
	resp, err := http.Get(pythonURL)
	if err != nil {
		sentry.CaptureException(err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to query anime database"})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var results interface{}
	json.Unmarshal(body, &results)

	sh.db.LogSearch(req.Query, 0, "anime")

	c.JSON(http.StatusOK, results)
}

// ConcurrentSearch searches both web and anime database concurrently
func (sh *SearchHandlers) ConcurrentSearch(c *gin.Context) {
	var req ConcurrentSearchRequest
	if err := c.BindJSON(&req); err != nil {
		sentry.CaptureException(err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	result := ConcurrentSearchResult{}

	// Run both searches concurrently
	webChan := make(chan []SearchResult)
	animeChan := make(chan []map[string]interface{})
	errChan := make(chan error)

	// Web search
	go func() {
		cacheKey := fmt.Sprintf("web_search:%s", req.Query)
		var results []SearchResult

		if err := sh.cache.Get(ctx, cacheKey, &results); err == nil {
			webChan <- results
			return
		}

		// Fetch and cache
		results = []SearchResult{{Title: "Result", URL: "http://example.com", Snippet: "Search result"}}
		sh.cache.Set(ctx, cacheKey, results, 1*time.Hour)
		webChan <- results
	}()

	// Anime search
	go func() {
		pythonURL := "http://localhost:8000/api/search/semantic?query_text=" + req.Query + "&limit=3"
		resp, err := http.Get(pythonURL)
		if err != nil {
			errChan <- err
			return
		}
		defer resp.Body.Close()

		var results []services.SearchResult
		body, _ := io.ReadAll(resp.Body)
		json.Unmarshal(body, &results)
		animeChan <- results
	}()

	// Wait for results
	for i := 0; i < 2; i++ {
		select {
		case web := <-webChan:
			result.Web = web
		case anime := <-animeChan:
			result.Anime = anime
		case err := <-errChan:
			sentry.CaptureException(err)
		case <-ctx.Done():
			c.JSON(http.StatusRequestTimeout, gin.H{"error": "Search timeout"})
			return
		}
	}

	sh.db.LogSearch(req.Query, len(result.Web)+len(result.Anime), "concurrent")
	c.JSON(http.StatusOK, result)
}

// GetSearchHistory returns recent search history
func (sh *SearchHandlers) GetSearchHistory(c *gin.Context) {
	limit := 50
	history, err := sh.db.GetSearchHistory(limit)
	if err != nil {
		sentry.CaptureException(err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch history"})
		return
	}

	c.JSON(http.StatusOK, history)
}

// GetSearchStats returns search statistics
func (sh *SearchHandlers) GetSearchStats(c *gin.Context) {
	stats, err := sh.db.GetSearchStats()
	if err != nil {
		sentry.CaptureException(err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch stats"})
		return
	}

	// Add cache stats
	cacheStats, _ := sh.cache.GetStats(c)
	stats["cache"] = cacheStats

	c.JSON(http.StatusOK, stats)
}
