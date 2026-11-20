package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"anime-search-service/cache"
	"anime-search-service/consumers"
	"anime-search-service/db"
	"anime-search-service/handlers"
	"anime-search-service/monitoring"

	"github.com/getsentry/sentry-go"
	"github.com/gin-gonic/gin"
)

func main() {
	// Initialize Sentry for error tracking
	sentryDSN := os.Getenv("SENTRY_DSN")
	if sentryDSN != "" {
		if err := sentry.Init(sentry.ClientOptions{
			Dsn:         sentryDSN,
			Environment: os.Getenv("ENVIRONMENT"),
			// 10%: enough signal for a portfolio, well inside the free quota
			TracesSampleRate: 0.1,
		}); err != nil {
			log.Printf("Sentry initialization failed: %v", err)
		}
		defer sentry.Flush(2 * 1000)
	}

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

	// The browser calls this service directly from the frontend's origin, so it needs
	// its own CORS headers; the Python backend sets its own and nginx must not add a
	// second copy. CORS_ORIGIN pins it to the deployed frontend; "*" in development.
	corsOrigin := os.Getenv("CORS_ORIGIN")
	if corsOrigin == "" {
		corsOrigin = "*"
	}
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", corsOrigin)
		c.Header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type")
		c.Header("Vary", "Origin")
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	})

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

	// Start Kafka consumers in a separate goroutine
	go func() {
		consumers.StartConsumers(dbConn)
	}()

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8001"
	}

	log.Printf("🚀 Starting Go search service on port %s", port)
	if err := router.Run(":" + port); err != nil {
		sentry.CaptureException(err)
		log.Fatalf("❌ Server failed to start: %v", err)
	}
}
