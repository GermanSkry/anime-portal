package consumers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"anime-search-service/db"
	"anime-search-service/kafka"
)

// NewDBConsumer saves chat messages to PostgreSQL.
func NewDBConsumer(conn *db.Connection) *Consumer {
	return newConsumer("DB Consumer", "processed", "chat.messages-db", func(ctx context.Context, event *kafka.ChatMessageEvent) error {
		return saveToDB(ctx, conn, event)
	})
}

// saveToDB saves the chat message to database with idempotency check
func saveToDB(ctx context.Context, conn *db.Connection, event *kafka.ChatMessageEvent) error {
	sqlDB := conn.DB()

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
	refsJSON, err := json.Marshal(event.AnimeReferences)
	if err != nil {
		return fmt.Errorf("could not encode anime references: %w", err)
	}

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
		`INSERT INTO processed_messages (topic, message_id, processed_at)
		 VALUES ($1, $2, $3)
		 ON CONFLICT (message_id) DO NOTHING`,
		"chat.messages", event.MessageID, time.Now(),
	)

	if err != nil {
		log.Printf("⚠️  Warning: could not mark as processed (non-critical): %v", err)
	}

	return nil
}
