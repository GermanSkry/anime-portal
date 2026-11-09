package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	kfg "github.com/segmentio/kafka-go"
)

// ChatMessageEvent represents a chat message event from Kafka
type ChatMessageEvent struct {
	MessageID        string `json:"message_id"`
	UserID           string `json:"user_id"`
	Message          string `json:"message"`
	Response         string `json:"response"`
	AnimeReferences  []struct {
		Title string `json:"title"`
		ID    int    `json:"id"`
	} `json:"anime_references"`
	AnimeContextID int    `json:"anime_context_id"`
	Timestamp      string `json:"timestamp"`
}

// RetryConfig for exponential backoff
type RetryConfig struct {
	MaxRetries  int
	BackoffMs   []int
	DLQTopic    string
}

// DefaultRetryConfig returns standard retry config
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxRetries: 3,
		BackoffMs:  []int{1000, 2000, 4000},
		DLQTopic:   "dlq.failed_messages",
	}
}

// NewReader creates a new Kafka reader
func NewReader(topic string) *kfg.Reader {
	brokers := strings.Split(os.Getenv("KAFKA_BROKERS"), ",")
	if len(brokers) == 0 || brokers[0] == "" {
		brokers = []string{"localhost:9092"}
	}

	return kfg.NewReader(kfg.ReaderConfig{
		Brokers:        brokers,
		Topic:          topic,
		GroupID:        fmt.Sprintf("%s-consumer", topic),
		StartOffset:    kfg.LastOffset,
		CommitInterval: time.Second,
		MaxBytes:       10e6,
	})
}

// NewWriter creates a new Kafka writer (for DLQ, etc)
func NewWriter(topic string) *kfg.Writer {
	brokers := strings.Split(os.Getenv("KAFKA_BROKERS"), ",")
	if len(brokers) == 0 || brokers[0] == "" {
		brokers = []string{"localhost:9092"}
	}

	return &kfg.Writer{
		Addr:     kfg.TCP(brokers...),
		Topic:    topic,
		Balancer: &kfg.LeastBytes{},
	}
}

// SendToDLQ sends a failed message to the dead letter queue
func SendToDLQ(ctx context.Context, writer *kfg.Writer, originalTopic string, msg kfg.Message, err error, retriesAttempted int) error {
	dlqMessage := map[string]interface{}{
		"original_topic":    originalTopic,
		"original_message":  string(msg.Value),
		"error":             err.Error(),
		"retries_attempted": retriesAttempted,
		"timestamp":         time.Now().Format(time.RFC3339),
		"offset":            msg.Offset,
		"partition":         msg.Partition,
	}

	data, _ := json.Marshal(dlqMessage)

	return writer.WriteMessages(ctx, kfg.Message{
		Value: data,
	})
}

// ParseEvent unmarshals a Kafka message into ChatMessageEvent
func ParseEvent(data []byte) (*ChatMessageEvent, error) {
	var event ChatMessageEvent
	err := json.Unmarshal(data, &event)
	return &event, err
}

// CreateTopics creates required Kafka topics (run once)
func CreateTopics(brokers []string) error {
	if len(brokers) == 0 {
		brokers = strings.Split(os.Getenv("KAFKA_BROKERS"), ",")
	}
	if len(brokers) == 0 || brokers[0] == "" {
		brokers = []string{"localhost:9092"}
	}

	conn, err := kfg.Dial("tcp", brokers[0])
	if err != nil {
		return fmt.Errorf("failed to connect to Kafka: %w", err)
	}
	defer conn.Close()

	topics := []kfg.TopicConfig{
		{
			Topic:             "chat.messages",
			NumPartitions:     3,
			ReplicationFactor: 1,
		},
		{
			Topic:             "search.updates",
			NumPartitions:     3,
			ReplicationFactor: 1,
		},
		{
			Topic:             "dlq.failed_messages",
			NumPartitions:     1,
			ReplicationFactor: 1,
		},
	}

	err = conn.CreateTopics(topics...)
	if err != nil {
		// Topics might already exist, that's ok
		log.Printf("Topics create result: %v", err)
	}

	return nil
}
