package consumers

import (
	"context"
	"log"
	"time"

	"anime-search-service/db"
	"anime-search-service/kafka"
)

// NewSearchIndexer updates the search index when anime is mentioned in chat.
func NewSearchIndexer(conn *db.Connection) *Consumer {
	return newConsumer("Search Indexer", "indexed", "chat.messages-indexer", func(ctx context.Context, event *kafka.ChatMessageEvent) error {
		return indexSearch(ctx, conn, event)
	})
}

// indexSearch updates the search index for anime mentioned in the chat
func indexSearch(ctx context.Context, conn *db.Connection, event *kafka.ChatMessageEvent) error {
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
		_, err := conn.DB().ExecContext(ctx,
			`INSERT INTO search_engagement (anime_id, engagement_type, count, last_updated)
			 VALUES ($1, $2, $3, $4)
			 ON CONFLICT (anime_id, engagement_type)
			 DO UPDATE SET count = search_engagement.count + 1, last_updated = $4`,
			animeID, "chat_mention", 1, time.Now(),
		)

		if err != nil {
			// engagement is a ranking signal, not the message itself: log and keep going
			log.Printf("⚠️ Could not update search engagement for anime %d: %v", animeID, err)
		}
	}

	log.Printf("📊 Indexed %d anime for search: %v", len(animeIDs), animeIDs)
	return nil
}
