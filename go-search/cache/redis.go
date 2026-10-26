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
