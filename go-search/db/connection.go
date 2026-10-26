package db

import (
	"database/sql"
	"log"

	_ "github.com/lib/pq"
)

type Connection struct {
	db *sql.DB
}

func NewConnection(databaseURL string) *Connection {
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	if err := db.Ping(); err != nil {
		log.Fatalf("Failed to ping database: %v", err)
	}

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)

	return &Connection{db: db}
}

// LogSearch logs a search query to the database
func (c *Connection) LogSearch(query string, resultCount int, queryType string) error {
	_, err := c.db.Exec(
		`INSERT INTO search_history (query, result_count, query_type, created_at)
		 VALUES ($1, $2, $3, NOW())`,
		query, resultCount, queryType,
	)
	return err
}

// GetSearchHistory retrieves recent searches
func (c *Connection) GetSearchHistory(limit int) ([]map[string]interface{}, error) {
	rows, err := c.db.Query(
		`SELECT id, query, result_count, query_type, created_at
		 FROM search_history
		 ORDER BY created_at DESC
		 LIMIT $1`,
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []map[string]interface{}
	for rows.Next() {
		var id int
		var query, queryType string
		var resultCount int
		var createdAt string

		if err := rows.Scan(&id, &query, &resultCount, &queryType, &createdAt); err != nil {
			return nil, err
		}

		results = append(results, map[string]interface{}{
			"id":            id,
			"query":         query,
			"result_count":  resultCount,
			"query_type":    queryType,
			"created_at":    createdAt,
		})
	}

	return results, rows.Err()
}

// GetSearchStats returns search statistics
func (c *Connection) GetSearchStats() (map[string]interface{}, error) {
	var totalSearches, uniqueQueries int

	err := c.db.QueryRow(`
		SELECT COUNT(*), COUNT(DISTINCT query) FROM search_history
	`).Scan(&totalSearches, &uniqueQueries)

	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"total_searches":  totalSearches,
		"unique_queries":  uniqueQueries,
	}, nil
}

// Close closes the database connection
func (c *Connection) Close() error {
	return c.db.Close()
}
