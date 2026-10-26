package utils

import (
	"regexp"
	"sort"
	"strings"
)

// NormalizeQuery normalizes a search query for better cache hits
// Handles: case sensitivity, extra spaces, word order
func NormalizeQuery(query string) string {
	// 1. Lowercase
	normalized := strings.ToLower(query)

	// 2. Remove extra spaces and trim
	normalized = strings.TrimSpace(normalized)
	normalized = regexp.MustCompile(`\s+`).ReplaceAllString(normalized, " ")

	// 3. Remove common words that don't affect meaning
	stopwords := map[string]bool{
		"a": true, "an": true, "the": true,
		"and": true, "or": true, "but": true,
		"is": true, "are": true, "was": true,
		"to": true, "for": true, "of": true,
		"in": true, "on": true, "at": true,
		"be": true, "by": true, "from": true,
	}

	words := strings.Fields(normalized)
	var filtered []string
	for _, word := range words {
		if !stopwords[word] {
			filtered = append(filtered, word)
		}
	}

	// 4. Sort words alphabetically for consistent cache keys
	// "best anime 2026" → "2026 anime best"
	// "anime best 2026" → "2026 anime best"
	// Both become same cache key!
	sort.Strings(filtered)

	return strings.Join(filtered, " ")
}
