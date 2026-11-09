-- Kafka Phase 3 Tables

-- Track processed messages for idempotent consumption
CREATE TABLE IF NOT EXISTS processed_messages (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    message_id UUID NOT NULL,
    offset BIGINT NOT NULL DEFAULT 0,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(topic, message_id)
);

CREATE INDEX IF NOT EXISTS idx_processed_messages_message_id ON processed_messages(message_id);
CREATE INDEX IF NOT EXISTS idx_processed_messages_topic ON processed_messages(topic);

-- Track search engagement (anime popularity from chats)
CREATE TABLE IF NOT EXISTS search_engagement (
    id SERIAL PRIMARY KEY,
    anime_id INTEGER NOT NULL REFERENCES anime(id) ON DELETE CASCADE,
    engagement_type VARCHAR(50) NOT NULL, -- 'chat_mention', 'search_click', etc
    count INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(anime_id, engagement_type)
);

CREATE INDEX IF NOT EXISTS idx_search_engagement_anime_id ON search_engagement(anime_id);
CREATE INDEX IF NOT EXISTS idx_search_engagement_type ON search_engagement(engagement_type);
