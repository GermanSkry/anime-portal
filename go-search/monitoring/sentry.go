package monitoring

import (
	"log"

	"github.com/getsentry/sentry-go"
)

// Init initializes monitoring (called from main)
func Init() {
	log.Println("Monitoring initialized")
}

// CaptureError captures and reports an error
func CaptureError(err error) {
	sentry.CaptureException(err)
}

// CaptureMessage captures a message
func CaptureMessage(msg string) {
	sentry.CaptureMessage(msg)
}

// CapturePanic recovers from panic and reports it
func CapturePanic() {
	if r := recover(); r != nil {
		sentry.CaptureException(r.(error))
		panic(r)
	}
}
