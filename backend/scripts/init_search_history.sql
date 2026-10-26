-- Create search_history table for Phase 5 (Go microservice)

CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    query VARCHAR(255) NOT NULL,
    result_count INTEGER,
    query_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for analytics queries
CREATE INDEX IF NOT EXISTS idx_query_type ON search_history(query_type);
CREATE INDEX IF NOT EXISTS idx_query_created ON search_history(query, created_at);

-- Grant permissions (if needed)
-- GRANT SELECT, INSERT ON search_history TO your_app_user;
