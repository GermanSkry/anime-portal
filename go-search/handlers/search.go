package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"anime-search-service/cache"
	"anime-search-service/db"
	"anime-search-service/services"
	"anime-search-service/utils"

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
	Anime []services.SearchResult `json:"anime"`
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
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	startTime := time.Now()
	// Normalize query for better cache hits
	// "best anime 2026" and "anime best 2026" become same cache key
	normalizedQuery := utils.NormalizeQuery(req.Query)
	cacheKey := fmt.Sprintf("web_search:%s", normalizedQuery)

	// Check cache first (exact + normalized match)
	var results []services.SearchResult
	if err := sh.cache.Get(ctx, cacheKey, &results); err == nil {
		sh.analytics.TrackCacheHit(req.Query)
		sh.db.LogSearch(req.Query, len(results), "web_cached")
		c.JSON(http.StatusOK, results)
		return
	}

	// Try semantic similarity (Option 2)
	// Get embedding for current query
	embeddingClient := utils.NewEmbeddingClient("http://localhost:8000")
	if embedding, err := embeddingClient.GetEmbedding(req.Query); err == nil {
		// Search for semantically similar cached queries
		// 0.78 threshold: balances cache hits vs false positives
		// Avoids opposite meanings (e.g., "best" vs "worst" is 0.82 but different)
		if similarKey, err := sh.cache.GetSimilarQueries(ctx, embedding, 0.78); err == nil && similarKey != "" {
			// Found semantic match! Extract original query and use cache
			if err := sh.cache.Get(ctx, similarKey, &results); err == nil {
				sh.analytics.TrackCacheHit(req.Query)
				sh.db.LogSearch(req.Query, len(results), "web_semantic_cached")
				log.Printf("Semantic cache hit: '%s' matched '%s'", req.Query, similarKey)
				c.JSON(http.StatusOK, results)
				return
			}
		}
	}

	// Cache miss - fetch from SerpAPI
	sh.analytics.TrackCacheMiss(req.Query)

	results, err := sh.serpapi.Search(req.Query, 3)
	if err != nil {
		sh.analytics.TrackAPICall("serpapi", false, time.Since(startTime))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to search web"})
		return
	}

	// Store in cache for 1 hour
	sh.cache.Set(ctx, cacheKey, results, 1*time.Hour)

	// Store embedding for semantic similarity matching (Option 2)
	// Get embedding and cache it for future semantic matches
	if embeddingClient := utils.NewEmbeddingClient("http://localhost:8000"); embeddingClient != nil {
		if embedding, err := embeddingClient.GetEmbedding(req.Query); err == nil {
			// Store embedding with normalized query key
			embeddingKey := fmt.Sprintf("embedding:%s", normalizedQuery)
			sh.cache.StoreEmbedding(ctx, normalizedQuery, embedding)
			log.Printf("Stored embedding for '%s' (key: %s)", req.Query, embeddingKey)
		}
	}

	sh.analytics.TrackAPICall("serpapi", true, time.Since(startTime))
	sh.analytics.TrackSearch(req.Query, len(results), "web", time.Since(startTime))
	sh.db.LogSearch(req.Query, len(results), "web")

	c.JSON(http.StatusOK, results)
}

// SearchAnime calls the Python FastAPI anime endpoint
func (sh *SearchHandlers) SearchAnime(c *gin.Context) {
	var req SearchRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	// Call Python FastAPI backend
	pythonURL := "http://localhost:8000/api/search/semantic?query_text=" + req.Query + "&limit=3"
	resp, err := http.Get(pythonURL)
	if err != nil {
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
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	result := ConcurrentSearchResult{}
	webChan := make(chan []services.SearchResult)
	animeChan := make(chan []services.SearchResult)
	errChan := make(chan error)

	// Web search
	go func() {
		cacheKey := fmt.Sprintf("web_search:%s", req.Query)
		var results []services.SearchResult

		if err := sh.cache.Get(ctx, cacheKey, &results); err == nil {
			webChan <- results
			return
		}

		// Fetch and cache
		searchResults, _ := sh.serpapi.Search(req.Query, 3)
		sh.cache.Set(ctx, cacheKey, searchResults, 1*time.Hour)
		webChan <- searchResults
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
		case <-errChan:
			// error logged but continue
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
		log.Printf("GetSearchHistory error: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch history"})
		return
	}

	if history == nil {
		history = make([]map[string]interface{}, 0)
	}
	c.JSON(http.StatusOK, history)
}

// GetSearchStats returns search statistics
func (sh *SearchHandlers) GetSearchStats(c *gin.Context) {
	stats, err := sh.db.GetSearchStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to fetch stats"})
		return
	}

	// Add cache stats
	cacheStats, _ := sh.cache.GetStats(c)
	stats["cache"] = cacheStats

	c.JSON(http.StatusOK, stats)
}
