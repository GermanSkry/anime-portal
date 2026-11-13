package utils

import "log"

// LogErr surfaces failures from fire-and-forget calls (telemetry, cache writes,
// audit logging) without turning them into request failures.
func LogErr(what string, err error) {
	if err != nil {
		log.Printf("⚠️ %s: %v", what, err)
	}
}
