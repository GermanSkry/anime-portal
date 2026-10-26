package utils

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"time"
)

// EmbeddingClient handles semantic query similarity
type EmbeddingClient struct {
	baseURL string
	client  *http.Client
}

// EmbeddingResponse from Python backend
type EmbeddingResponse struct {
	Embedding []float32 `json:"embedding"`
}

// NewEmbeddingClient creates a client for embedding API
func NewEmbeddingClient(pythonBackendURL string) *EmbeddingClient {
	return &EmbeddingClient{
		baseURL: pythonBackendURL,
		client: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

// GetEmbedding calls the Python backend to get query embedding
func (e *EmbeddingClient) GetEmbedding(query string) ([]float32, error) {
	payload := map[string]string{
		"text": query,
	}

	data, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", e.baseURL+"/api/embedding", bytes.NewBuffer(data))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := e.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var embResp EmbeddingResponse
	if err := json.Unmarshal(body, &embResp); err != nil {
		return nil, err
	}

	return embResp.Embedding, nil
}

// CosineSimilarity calculates cosine similarity between two vectors
// Returns value between 0 and 1 (1 = identical, 0 = completely different)
func CosineSimilarity(a, b []float32) float32 {
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

// sqrt is a simple square root implementation
func sqrt(x float32) float32 {
	if x < 0 {
		return 0
	}
	// Newton's method for square root
	z := x
	for i := 0; i < 10; i++ {
		z = (z + x/z) / 2
	}
	return z
}
