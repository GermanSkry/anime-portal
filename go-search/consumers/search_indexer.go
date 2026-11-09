package consumers

import (
	"context"
	"fmt"
	"log"
	"time"

	kfg "github.com/segmentio/kafka-go"
	"anime-search-service/db"
	"anime-search-service/kafka"
)

// SearchIndexer updates search index when anime is mentioned in chat
type SearchIndexer struct {
	reader *kfg.Reader
	writer *kfg.Writer
	conn   *db.Connection
	config kafka.RetryConfig
}

// NewSearchIndexer creates a new search indexer consumer
func NewSearchIndexer(conn *db.Connection) *SearchIndexer {
	return &SearchIndexer{
		reader: kafka.NewReader("chat.messages"),
		writer: kafka.NewWriter("dlq.failed_messages"),
		conn:   conn,
		config: kafka.DefaultRetryConfig(),
	}
}

// Start begins consuming messages
func (s *SearchIndexer) Start(ctx context.Context) {
	log.Println("🚀 Search Indexer starting...")

	for {
		select {
		case <-ctx.Done():
			s.reader.Close()
			s.writer.Close()
			log.Println("✅ Search Indexer stopped")
			return
		default:
		}

		msg, err := s.reader.FetchMessage(ctx)
		if err != nil {
			log.Printf("❌ Error fetching message: %v", err)
			time.Sleep(time.Second)
			continue
		}

		if err := s.processWithRetry(ctx, msg); err != nil {
			log.Printf("❌ All retries failed for message: %v", err)
			kafka.SendToDLQ(ctx, s.writer, "chat.messages", msg, err, s.config.MaxRetries)
			continue
		}

		s.reader.CommitMessages(ctx, msg)
		log.Printf("✅ Message indexed: %s", msg.Key)
	}
}

// processWithRetry attempts to index with exponential backoff
func (s *SearchIndexer) processWithRetry(ctx context.Context, msg kfg.Message) error {
	var lastErr error

	for attempt := 0; attempt < s.config.MaxRetries; attempt++ {
		event, err := kafka.ParseEvent(msg.Value)
		if err != nil {
			return fmt.Errorf("invalid message format: %w", err)
		}

		lastErr = s.indexSearch(ctx, event)
		if lastErr == nil {
			return nil
		}

		log.Printf("⚠️ Attempt %d failed: %v, retrying in %dms...",
			attempt+1, lastErr, s.config.BackoffMs[attempt])

		time.Sleep(time.Duration(s.config.BackoffMs[attempt]) * time.Millisecond)
	}

	return lastErr
}

// indexSearch updates the search index for anime mentioned in the chat
func (s *SearchIndexer) indexSearch(ctx context.Context, event *kafka.ChatMessageEvent) error {
	if len(event.AnimeReferences) == 0 {
		log.Printf("⏭️  No anime references to index for message: %s", event.MessageID)
		return nil
	}

	// Extract anime IDs from references
	animeIDs := make([]int, len(event.AnimeReferences))
	for i, ref := range event.AnimeReferences {
		animeIDs[i] = ref.ID
	}

	// Record search engagement for each anime mentioned
	// This updates search popularity/ranking based on chat mentions
	for _, animeID := range animeIDs {
		_, err := s.conn.DB().ExecContext(ctx,
			`INSERT INTO search_engagement (anime_id, engagement_type, count, last_updated)
			 VALUES ($1, $2, $3, $4)
			 ON CONFLICT (anime_id, engagement_type)
			 DO UPDATE SET count = count + 1, last_updated = $4`,
			animeID, "chat_mention", 1, time.Now(),
		)

		if err != nil {
			// If table doesn't exist, just log and continue
			log.Printf("⚠️ Could not update search engagement (table might not exist): %v", err)
			// Don't fail the whole operation for this
		}
	}

	log.Printf("📊 Indexed %d anime for search: %v", len(animeIDs), animeIDs)
	return nil
}
