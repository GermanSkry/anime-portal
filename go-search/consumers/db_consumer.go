package consumers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	kfg "github.com/segmentio/kafka-go"
	"anime-search-service/db"
	"anime-search-service/kafka"
)

// DBConsumer saves chat messages to PostgreSQL
type DBConsumer struct {
	reader *kfg.Reader
	writer *kfg.Writer
	conn   *db.Connection
	config kafka.RetryConfig
}

// NewDBConsumer creates a new DB consumer
func NewDBConsumer(conn *db.Connection) *DBConsumer {
	return &DBConsumer{
		reader: kafka.NewReader("chat.messages"),
		writer: kafka.NewWriter("dlq.failed_messages"),
		conn:   conn,
		config: kafka.DefaultRetryConfig(),
	}
}

// Start begins consuming messages
func (c *DBConsumer) Start(ctx context.Context) {
	log.Println("🚀 DB Consumer starting...")

	for {
		select {
		case <-ctx.Done():
			c.reader.Close()
			c.writer.Close()
			log.Println("✅ DB Consumer stopped")
			return
		default:
		}

		msg, err := c.reader.FetchMessage(ctx)
		if err != nil {
			log.Printf("❌ Error fetching message: %v", err)
			time.Sleep(time.Second)
			continue
		}

		// Process with retry logic
		if err := c.processWithRetry(ctx, msg); err != nil {
			log.Printf("❌ All retries failed for message %s: %v", msg.Key, err)
			kafka.SendToDLQ(ctx, c.writer, "chat.messages", msg, err, c.config.MaxRetries)
			continue
		}

		// Mark as processed
		c.reader.CommitMessages(ctx, msg)
		log.Printf("✅ Message processed: %s", msg.Key)
	}
}

// processWithRetry attempts to save with exponential backoff
func (c *DBConsumer) processWithRetry(ctx context.Context, msg kfg.Message) error {
	var lastErr error

	for attempt := 0; attempt < c.config.MaxRetries; attempt++ {
		event, err := kafka.ParseEvent(msg.Value)
		if err != nil {
			return fmt.Errorf("invalid message format: %w", err)
		}

		lastErr = c.saveToDB(ctx, event)
		if lastErr == nil {
			return nil
		}

		log.Printf("⚠️ Attempt %d failed: %v, retrying in %dms...",
			attempt+1, lastErr, c.config.BackoffMs[attempt])

		time.Sleep(time.Duration(c.config.BackoffMs[attempt]) * time.Millisecond)
	}

	return lastErr
}

// saveToDB saves the chat message to database with idempotency check
func (c *DBConsumer) saveToDB(ctx context.Context, event *kafka.ChatMessageEvent) error {
	sqlDB := c.conn.DB()

	// Check if already processed (idempotent)
	var exists bool
	err := sqlDB.QueryRowContext(ctx,
		"SELECT EXISTS(SELECT 1 FROM processed_messages WHERE message_id = $1)",
		event.MessageID,
	).Scan(&exists)

	if err != nil {
		return fmt.Errorf("idempotency check failed: %w", err)
	}

	if exists {
		log.Printf("⏭️  Message already processed: %s", event.MessageID)
		return nil
	}

	// Convert anime references to JSON
	refsJSON, _ := json.Marshal(event.AnimeReferences)

	// Save to chat_history
	_, err = sqlDB.ExecContext(ctx,
		`INSERT INTO chat_history (user_ip, user_message, assistant_response, anime_context_id, anime_references)
		 VALUES ($1, $2, $3, $4, $5)`,
		event.UserID, event.Message, event.Response, event.AnimeContextID, string(refsJSON),
	)

	if err != nil {
		return fmt.Errorf("failed to insert chat: %w", err)
	}

	// Mark as processed
	_, err = sqlDB.ExecContext(ctx,
		`INSERT INTO processed_messages (topic, message_id, offset, processed_at)
		 VALUES ($1, $2, $3, $4)`,
		"chat.messages", event.MessageID, 0, time.Now(),
	)

	if err != nil {
		log.Printf("⚠️  Warning: could not mark as processed (non-critical): %v", err)
	}

	return nil
}
