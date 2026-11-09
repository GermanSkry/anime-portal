package consumers

import (
	"context"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"anime-search-service/db"
	"anime-search-service/kafka"
)

// StartConsumers starts all Kafka consumers
func StartConsumers(conn *db.Connection) {
	ctx, cancel := context.WithCancel(context.Background())

	// Create topics
	log.Println("📋 Creating Kafka topics...")
	if err := kafka.CreateTopics(nil); err != nil {
		log.Printf("⚠️ Failed to create topics (might already exist): %v", err)
	}

	// Create consumers
	dbConsumer := NewDBConsumer(conn)
	searchIndexer := NewSearchIndexer(conn)

	// Run consumers in parallel
	var wg sync.WaitGroup

	log.Println("🚀 Starting Kafka consumers...")

	// Start DB consumer
	wg.Add(1)
	go func() {
		defer wg.Done()
		dbConsumer.Start(ctx)
	}()

	// Start search indexer
	wg.Add(1)
	go func() {
		defer wg.Done()
		searchIndexer.Start(ctx)
	}()

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	<-sigChan
	log.Println("\n🛑 Shutdown signal received, stopping consumers...")

	cancel()
	wg.Wait()

	log.Println("✅ All consumers stopped")
}
