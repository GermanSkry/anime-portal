"""Turning a chat message into database search terms.

Its own module, and deliberately stdlib-only: the catalogue search lives beside
an OpenAI client and a psycopg connection, and this pure text helper should not
drag those in — not for callers, and not for its tests.
"""
import re

# Words that carry no meaning for a catalogue search. Genre words (action, drama,
# romance, mecha...) are deliberately absent: those are exactly what we want to match.
_FILLER = {
    "a", "an", "the", "some", "any", "one", "two", "me", "my", "i", "you", "it",
    "is", "are", "was", "were", "be", "can", "could", "would", "will", "do", "does",
    "and", "or", "but", "for", "with", "about", "like", "that", "this", "these",
    "of", "to", "in", "on", "at", "from", "by", "as",
    "anime", "series", "show", "shows", "movie", "movies", "title", "titles",
    "recommend", "recommendation", "recommendations", "suggest", "suggestion",
    "find", "search", "looking", "look", "want", "give", "tell", "name", "list",
    "good", "great", "best", "nice", "cool", "popular", "please", "something",
    "what", "whats", "which", "who", "how", "where", "when", "why", "short", "long",
    "anything", "anyone", "there", "here", "hello", "hey", "hi", "thanks", "thank",
    "yes", "not", "dont", "cant", "really", "very", "more", "also", "then", "than",
    "them", "they", "your", "their", "have", "has", "had", "get", "got", "make",
}


def extract_terms(query: str) -> list[str]:
    """Pull the searchable words out of a sentence.

    The agent hands us whole messages like "suggest a mecha anime", which match no
    title, plot or genre as a single string. Searching the words separately does.
    """
    words = [w.replace("'", "") for w in re.findall(r"[a-z0-9']+", query.lower())]
    terms = []
    for w in words:
        if len(w) <= 2 or w in _FILLER or w in terms:
            continue
        terms.append(w)
        # "ninjas" must find "ninja"; crude but it covers the plurals people type
        singular = w[:-1]
        if w.endswith("s") and not w.endswith("ss") and len(singular) > 2 and singular not in _FILLER:
            terms.append(singular)
    # nothing but filler: fall back to the raw phrase rather than matching everything
    return terms or ([query.strip()] if query.strip() else [])
