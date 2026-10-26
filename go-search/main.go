package main

import (
	"context"
	"log"
	"os"

	"anime-search-service/cache"
	"anime-search-service/db"
	"anime-search-service/handlers"
	"anime-search-service/monitoring"

	"github.com/gin-gonic/gin"
	"github.com/getsentry/sentry-go"
)

func main() {
	// Initialize Sentry for error tracking
	if err := sentry.Init(sentry.ClientOptions{
		Dsn:     os.Getenv("SENTRY_DSN"),
		Environment: os.Getenv("ENVIRONMENT"),
		TracesSampleRate: 1.0,
	}); err != nil {
		log.Printf("Sentry initialization failed: %v", err)
	}
	defer sentry.Flush(2 * 1000)

	// Initialize Redis cache
	redisClient := cache.NewRedisClient(os.Getenv("REDIS_URL"))
	defer redisClient.Close(context.Background())

	// Initialize database connection
	dbConn := db.NewConnection(os.Getenv("DATABASE_URL"))
	defer dbConn.Close()

	// Initialize monitoring
	monitoring.Init()

	// Create router
	router := gin.Default()

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// Search routes
	searchHandlers := handlers.NewSearchHandlers(redisClient, dbConn)

	router.POST("/api/search/web", searchHandlers.SearchWeb)
	router.POST("/api/search/anime", searchHandlers.SearchAnime)
	router.POST("/api/search/concurrent", searchHandlers.ConcurrentSearch)
	router.GET("/api/search/history", searchHandlers.GetSearchHistory)
	router.GET("/api/search/stats", searchHandlers.GetSearchStats)

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8001"
	}

	log.Printf("Starting Go search service on port %s", port)
	if err := router.Run(":" + port); err != nil {
		sentry.CaptureException(err)
		log.Fatalf("Server failed to start: %v", err)
	}
}
