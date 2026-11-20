package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"
)

type PostHogClient struct {
	apiKey string
	client *http.Client
}

type PostHogEvent struct {
	DistinctID string                 `json:"distinct_id"`
	Event      string                 `json:"event"`
	Timestamp  string                 `json:"timestamp"`
	Properties map[string]interface{} `json:"properties"`
}

type PostHogBatch struct {
	BatchKey string         `json:"batch_key"`
	Events   []PostHogEvent `json:"events"`
}

func NewPostHogClient() *PostHogClient {
	return &PostHogClient{
		apiKey: os.Getenv("POSTHOG_API_KEY"),
		client: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

// CaptureEvent sends an event to PostHog. distinctID must identify a visitor:
// PostHog counts unique users by it, so passing a constant collapses everyone
// into one "user" and makes every funnel and retention number meaningless.
func (p *PostHogClient) CaptureEvent(distinctID string, event string, properties map[string]interface{}) error {
	if p.apiKey == "" {
		return nil // Skip if API key not set
	}
	if distinctID == "" {
		distinctID = "anonymous"
	}

	evt := PostHogEvent{
		DistinctID: distinctID,
		Event:      event,
		Timestamp:  time.Now().Format(time.RFC3339),
		Properties: properties,
	}

	batch := PostHogBatch{
		BatchKey: p.apiKey,
		Events:   []PostHogEvent{evt},
	}

	data, err := json.Marshal(batch)
	if err != nil {
		return err
	}

	// POSTHOG_HOST overrides this, for a self-hosted instance or a local sink
	posthogURL := "https://eu.i.posthog.com/batch"
	if host := os.Getenv("POSTHOG_HOST"); host != "" {
		posthogURL = strings.TrimSuffix(host, "/") + "/batch"
	}
	req, err := http.NewRequest("POST", posthogURL, bytes.NewBuffer(data))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := p.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusNoContent {
		return fmt.Errorf("PostHog error: %d", resp.StatusCode)
	}

	return nil
}

// TrackSearch tracks a search event. The raw query is deliberately not sent:
// it is text the visitor typed, and query_length answers the same questions.
func (p *PostHogClient) TrackSearch(who string, query string, resultCount int, queryType string, duration time.Duration) error {
	properties := map[string]interface{}{
		"query_length": len(query),
		"result_count": resultCount,
		"zero_results": resultCount == 0,
		"query_type":   queryType,
		"duration_ms":  duration.Milliseconds(),
		"timestamp":    time.Now().Unix(),
	}

	return p.CaptureEvent(who, "search_performed", properties)
}

// TrackCacheHit tracks cache hit events
func (p *PostHogClient) TrackCacheHit(who string, query string, kind string) error {
	properties := map[string]interface{}{
		"query_length": len(query),
		"cache_kind":   kind, // "exact" or "semantic"
		"timestamp":    time.Now().Unix(),
	}

	return p.CaptureEvent(who, "cache_hit", properties)
}

// TrackCacheMiss tracks cache miss events
func (p *PostHogClient) TrackCacheMiss(who string, query string) error {
	properties := map[string]interface{}{
		"query_length": len(query),
		"timestamp":    time.Now().Unix(),
	}

	return p.CaptureEvent(who, "cache_miss", properties)
}

// TrackAPICall tracks API calls for quota monitoring
func (p *PostHogClient) TrackAPICall(who string, apiName string, success bool, duration time.Duration) error {
	properties := map[string]interface{}{
		"api":         apiName,
		"success":     success,
		"duration_ms": duration.Milliseconds(),
		"timestamp":   time.Now().Unix(),
	}

	return p.CaptureEvent(who, "api_call", properties)
}
