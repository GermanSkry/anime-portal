package consumers

import (
	"context"
	"fmt"
	"log"
	"time"

	"anime-search-service/kafka"

	kfg "github.com/segmentio/kafka-go"
)

// handler does the real work for one parsed event. It is the only thing that
// differs between consumers; everything else below is shared.
type handler func(context.Context, *kafka.ChatMessageEvent) error

// messageReader is what the loop needs from a Kafka reader. *kfg.Reader satisfies
// it; tests substitute a fake.
type messageReader interface {
	FetchMessage(context.Context) (kfg.Message, error)
	CommitMessages(context.Context, ...kfg.Message) error
	Close() error
}

// Consumer runs the read -> retry -> dead-letter -> commit loop for one topic.
type Consumer struct {
	name   string // for logs, e.g. "DB Consumer"
	verb   string // past tense for the success log, e.g. "processed"
	reader messageReader
	writer kafka.MessageWriter
	config kafka.RetryConfig
	handle handler
}

func newConsumer(name, verb, group string, handle handler) *Consumer {
	return &Consumer{
		name:   name,
		verb:   verb,
		reader: kafka.NewReader("chat.messages", group),
		writer: kafka.NewWriter("dlq.failed_messages"),
		config: kafka.DefaultRetryConfig(),
		handle: handle,
	}
}

// shouldCommit decides whether a message may be marked as handled.
// A message is handled when the work succeeded, or when it failed but reached
// the dead-letter queue. If the dead-letter send also failed the offset stays
// uncommitted, so the message is retried after a restart instead of lost.
func shouldCommit(processErr, dlqErr error) bool {
	return processErr == nil || dlqErr == nil
}

// Start begins consuming messages until ctx is cancelled.
func (c *Consumer) Start(ctx context.Context) {
	log.Printf("🚀 %s starting...", c.name)

	for {
		select {
		case <-ctx.Done():
			if err := c.reader.Close(); err != nil {
				log.Printf("⚠️ reader close: %v", err)
			}
			if err := c.writer.Close(); err != nil {
				log.Printf("⚠️ writer close: %v", err)
			}
			log.Printf("✅ %s stopped", c.name)
			return
		default:
		}

		msg, err := c.reader.FetchMessage(ctx)
		if err != nil {
			log.Printf("❌ Error fetching message: %v", err)
			time.Sleep(time.Second)
			continue
		}

		var dlqErr error
		processErr := c.processWithRetry(ctx, msg)
		if processErr != nil {
			log.Printf("❌ All retries failed for message %s: %v", msg.Key, processErr)
			dlqErr = kafka.SendToDLQ(ctx, c.writer, "chat.messages", msg, processErr, c.config.MaxRetries)
			if dlqErr != nil {
				log.Printf("❌ DLQ send failed: %v", dlqErr)
			}
		}

		if !shouldCommit(processErr, dlqErr) {
			log.Printf("⏭️  Offset not committed, message %s will be retried", msg.Key)
			continue
		}
		if err := c.reader.CommitMessages(ctx, msg); err != nil {
			log.Printf("❌ Commit failed for %s: %v", msg.Key, err)
			continue
		}

		if processErr != nil {
			log.Printf("📥 Message sent to DLQ: %s", msg.Key)
		} else {
			log.Printf("✅ Message %s: %s", c.verb, msg.Key)
		}
	}
}

// processWithRetry runs the handler with exponential backoff.
func (c *Consumer) processWithRetry(ctx context.Context, msg kfg.Message) error {
	var lastErr error

	for attempt := 0; attempt < c.config.MaxRetries; attempt++ {
		event, err := kafka.ParseEvent(msg.Value)
		if err != nil {
			return fmt.Errorf("invalid message format: %w", err)
		}

		lastErr = c.handle(ctx, event)
		if lastErr == nil {
			return nil
		}

		log.Printf("⚠️ Attempt %d failed: %v, retrying in %dms...",
			attempt+1, lastErr, c.config.BackoffMs[attempt])

		time.Sleep(time.Duration(c.config.BackoffMs[attempt]) * time.Millisecond)
	}

	return lastErr
}
