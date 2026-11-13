package consumers

import (
	"context"
	"errors"
	"testing"

	"anime-search-service/kafka"

	kfg "github.com/segmentio/kafka-go"
)

// A message may only be committed once it is safely handled: either the work
// succeeded, or it failed but reached the dead-letter queue. If both failed the
// offset must stay put so the message comes back after a restart.
func TestShouldCommit(t *testing.T) {
	work := errors.New("save failed")
	dlq := errors.New("dlq unreachable")

	cases := []struct {
		name       string
		processErr error
		dlqErr     error
		want       bool
	}{
		{"work succeeded", nil, nil, true},
		{"work failed, dlq took it", work, nil, true},
		{"work failed, dlq failed too", work, dlq, false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := shouldCommit(tc.processErr, tc.dlqErr); got != tc.want {
				t.Errorf("shouldCommit(%v, %v) = %v, want %v", tc.processErr, tc.dlqErr, got, tc.want)
			}
		})
	}
}

// --- fakes for the Start loop -------------------------------------------------

type fakeReader struct {
	msgs      []kfg.Message
	i         int
	committed []kfg.Message
	cancel    context.CancelFunc
}

func (f *fakeReader) FetchMessage(ctx context.Context) (kfg.Message, error) {
	if f.i >= len(f.msgs) {
		<-ctx.Done()
		return kfg.Message{}, ctx.Err()
	}
	m := f.msgs[f.i]
	f.i++
	if f.i == len(f.msgs) {
		// cancel now so the loop exits after handling this last message,
		// instead of sleeping on another fetch
		f.cancel()
	}
	return m, nil
}

func (f *fakeReader) CommitMessages(_ context.Context, msgs ...kfg.Message) error {
	f.committed = append(f.committed, msgs...)
	return nil
}
func (f *fakeReader) Close() error { return nil }

type fakeWriter struct {
	written []kfg.Message
	err     error
}

func (w *fakeWriter) WriteMessages(_ context.Context, msgs ...kfg.Message) error {
	if w.err != nil {
		return w.err
	}
	w.written = append(w.written, msgs...)
	return nil
}
func (w *fakeWriter) Close() error { return nil }

// runLoop drives one message through Start and reports what the loop did.
func runLoop(t *testing.T, work handler, dlqErr error) (*fakeReader, *fakeWriter) {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	reader := &fakeReader{
		msgs:   []kfg.Message{{Key: []byte("k1"), Value: []byte(`{"message_id":"m1"}`)}},
		cancel: cancel,
	}
	writer := &fakeWriter{err: dlqErr}

	c := &Consumer{
		name:   "Test Consumer",
		verb:   "processed",
		reader: reader,
		writer: writer,
		config: kafka.RetryConfig{MaxRetries: 1, BackoffMs: []int{0}},
		handle: work,
	}
	c.Start(ctx)
	return reader, writer
}

func TestStartCommitsHandledMessages(t *testing.T) {
	ok := func(context.Context, *kafka.ChatMessageEvent) error { return nil }
	boom := func(context.Context, *kafka.ChatMessageEvent) error { return errors.New("save failed") }
	dlqDown := errors.New("dlq unreachable")

	t.Run("work succeeded: committed, nothing dead-lettered", func(t *testing.T) {
		r, w := runLoop(t, ok, nil)
		if len(r.committed) != 1 {
			t.Errorf("committed %d messages, want 1", len(r.committed))
		}
		if len(w.written) != 0 {
			t.Errorf("wrote %d DLQ messages, want 0", len(w.written))
		}
	})

	t.Run("work failed but dlq took it: committed and dead-lettered", func(t *testing.T) {
		r, w := runLoop(t, boom, nil)
		if len(r.committed) != 1 {
			t.Errorf("committed %d messages, want 1", len(r.committed))
		}
		if len(w.written) != 1 {
			t.Errorf("wrote %d DLQ messages, want 1", len(w.written))
		}
	})

	t.Run("work and dlq both failed: not committed, so it is retried", func(t *testing.T) {
		r, _ := runLoop(t, boom, dlqDown)
		if len(r.committed) != 0 {
			t.Errorf("committed %d messages, want 0 - the message would be lost", len(r.committed))
		}
	})
}
