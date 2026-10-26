package cache

import (
	"context"
	"encoding/json"
	"time"

	"github.com/redis/go-redis/v9"
)

type RedisCache struct {
	client *redis.Client
}

func NewRedisClient(url string) *RedisCache {
	if url == "" {
		url = "redis://localhost:6379"
	}

	opt, _ := redis.ParseURL(url)
	client := redis.NewClient(opt)

	return &RedisCache{client: client}
}

// Get retrieves a value from cache
func (rc *RedisCache) Get(ctx context.Context, key string, v interface{}) error {
	data, err := rc.client.Get(ctx, key).Result()
	if err != nil {
		return err
	}
	return json.Unmarshal([]byte(data), v)
}

// Set stores a value in cache with TTL
func (rc *RedisCache) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return rc.client.Set(ctx, key, data, ttl).Err()
}

// GetOrSet gets from cache or sets if missing
func (rc *RedisCache) GetOrSet(ctx context.Context, key string, v interface{}, fetchFunc func() (interface{}, error), ttl time.Duration) error {
	// Try to get from cache
	if err := rc.Get(ctx, key, v); err == nil {
		return nil
	}

	// Cache miss - fetch from source
	data, err := fetchFunc()
	if err != nil {
		return err
	}

	// Store in cache
	if err := rc.Set(ctx, key, data, ttl); err != nil {
		// Log but don't fail if cache write fails
		return nil
	}

	// Unmarshal into result
	jsonData, _ := json.Marshal(data)
	return json.Unmarshal(jsonData, v)
}

// Delete removes a key from cache
func (rc *RedisCache) Delete(ctx context.Context, key string) error {
	return rc.client.Del(ctx, key).Err()
}

// Close closes the Redis connection
func (rc *RedisCache) Close(ctx context.Context) error {
	return rc.client.Close()
}

// GetStats returns cache statistics
func (rc *RedisCache) GetStats(ctx context.Context) (map[string]interface{}, error) {
	info, err := rc.client.Info(ctx, "stats").Result()
	if err != nil {
		return nil, err
	}

	return map[string]interface{}{
		"info": info,
	}, nil
}

// StoreEmbedding stores a query embedding for semantic similarity
func (rc *RedisCache) StoreEmbedding(ctx context.Context, query string, embedding []float32) error {
	key := "embedding:" + query
	data, err := json.Marshal(embedding)
	if err != nil {
		return err
	}
	// Store embeddings for 24 hours
	return rc.client.Set(ctx, key, data, 24*time.Hour).Err()
}

// GetSimilarQueries finds queries with similar embeddings
// Returns key of most similar query if similarity > threshold
func (rc *RedisCache) GetSimilarQueries(ctx context.Context, embedding []float32, threshold float32) (string, error) {
	// Get all embedding keys
	keys, err := rc.client.Keys(ctx, "embedding:*").Result()
	if err != nil || len(keys) == 0 {
		return "", err
	}

	var bestMatch string
	var bestSimilarity float32

	// For each stored embedding, calculate similarity
	for _, key := range keys {
		data, err := rc.client.Get(ctx, key).Result()
		if err != nil {
			continue
		}

		var storedEmbedding []float32
		if err := json.Unmarshal([]byte(data), &storedEmbedding); err != nil {
			continue
		}

		// Calculate cosine similarity
		similarity := cosineSimilarity(embedding, storedEmbedding)
		if similarity > threshold && similarity > bestSimilarity {
			bestMatch = key
			bestSimilarity = similarity
		}
	}

	return bestMatch, nil
}

// cosineSimilarity calculates similarity between vectors (0-1)
func cosineSimilarity(a, b []float32) float32 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct float32
	var magA float32
	var magB float32

	for i := range a {
		dotProduct += a[i] * b[i]
		magA += a[i] * a[i]
		magB += b[i] * b[i]
	}

	if magA == 0 || magB == 0 {
		return 0
	}

	return dotProduct / (sqrt(magA) * sqrt(magB))
}

// sqrt calculates square root
func sqrt(x float32) float32 {
	if x < 0 {
		return 0
	}
	z := x
	for i := 0; i < 10; i++ {
		z = (z + x/z) / 2
	}
	return z
}
