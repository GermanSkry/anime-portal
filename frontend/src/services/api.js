import { clientId } from './analytics'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GO_SEARCH_API = import.meta.env.VITE_GO_SEARCH_URL || 'http://localhost:8080'

// identifies the visitor to the backends, so their PostHog events and the
// browser's land on the same person
const idHeaders = (extra = {}) => {
  const id = clientId()
  return id ? { ...extra, 'X-Client-Id': id } : extra
}

// Anime API endpoints
export const animeAPI = {
  getAll: async (limit = 20) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime?limit=${limit}`, { headers: idHeaders() })
      const data = await res.json()
      return Array.isArray(data) ? data : []
    } catch (error) {
      console.error('Error fetching anime:', error)
      return []
    }
  },

  getById: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}`, { headers: idHeaders() })
      // 404 and 503 return an error object, which callers would render as a blank anime
      if (!res.ok) return null
      return await res.json()
    } catch (error) {
      console.error('Error fetching anime:', error)
      return null
    }
  },

  getByYear: async (year) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/year/${year}`, { headers: idHeaders() })
      return await res.json()
    } catch (error) {
      console.error('Error fetching anime by year:', error)
      return []
    }
  },

  getRelated: async (id, limit = 4) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}/related?limit=${limit}`, { headers: idHeaders() })
      return await res.json()
    } catch (error) {
      console.error('Error fetching related anime:', error)
      return []
    }
  },

  getSimilar: async (id, limit = 4, minRating = 6) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}/similar?limit=${limit}&min_rating=${minRating}`, { headers: idHeaders() })
      return await res.json()
    } catch (error) {
      console.error('Error fetching similar anime:', error)
      return []
    }
  }
}

// Search API endpoints (Go microservice)
export const searchAPI = {
  concurrent: async (query) => {
    try {
      const res = await fetch(`${GO_SEARCH_API}/api/search/concurrent`, {
        method: 'POST',
        headers: idHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ query })
      })
      return await res.json()
    } catch (error) {
      console.error('Error in concurrent search:', error)
      return { web: [], anime: [] }
    }
  },

  web: async (query) => {
    try {
      const res = await fetch(`${GO_SEARCH_API}/api/search/web`, {
        method: 'POST',
        headers: idHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ query })
      })
      return await res.json()
    } catch (error) {
      console.error('Error in web search:', error)
      return []
    }
  },

  anime: async (query) => {
    try {
      const res = await fetch(`${API_BASE}/api/search/semantic?query_text=${encodeURIComponent(query)}&limit=5`, { headers: idHeaders() })
      return await res.json()
    } catch (error) {
      console.error('Error in anime search:', error)
      return []
    }
  },

  // full-text + filter search over the whole catalogue. Not /api/search/anime:
  // that name is taken twice — a GET in chat.py that only scores the top 200 by
  // rating, and the Go service's POST — and neither filters the full catalogue.
  //
  // Every argument is optional and blank ones are left off, so this is the one
  // call behind a text search, a filter, or both at once. The server does the
  // work; Browse never downloads the catalogue to sift it in the browser.
  catalogue: async ({ q, genres, ratingMin, ratingMax, yearMin, yearMax, studio,
                      limit = 24, offset = 0 } = {}) => {
    const params = new URLSearchParams({ limit, offset })
    if (q) params.set('q', q)
    if (genres?.length) params.set('genres', genres.join(','))
    if (ratingMin != null) params.set('rating_min', ratingMin)
    if (ratingMax != null) params.set('rating_max', ratingMax)
    if (yearMin != null) params.set('year_min', yearMin)
    if (yearMax != null) params.set('year_max', yearMax)
    if (studio) params.set('studios', studio)
    try {
      const res = await fetch(`${API_BASE}/api/search?${params}`, { headers: idHeaders() })
      const data = await res.json()
      // an error response is an object, and callers render this straight into a list
      return Array.isArray(data) ? data : []
    } catch (error) {
      console.error('Error in catalogue search:', error)
      return []
    }
  },

  animeByTitle: (query, limit = 20) => searchAPI.catalogue({ q: query, limit }),
}

// Chat API endpoints
export const chatAPI = {
  send: async (message, context = '', animeId = null, messageHistory = []) => {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: idHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          message,
          context,
          anime_id: animeId,
          history: messageHistory
        })
      })
      return await res.json()
    } catch (error) {
      console.error('Error sending chat message:', error)
      return { response: 'Error connecting to chat service' }
    }
  },

  getHistory: async (animeId = null, limit = 20) => {
    try {
      const query = animeId ? `?limit=${limit}&anime_id=${animeId}` : `?limit=${limit}`
      const res = await fetch(`${API_BASE}/api/chat/history${query}`, { headers: idHeaders() })
      return await res.json()
    } catch (error) {
      console.error('Error fetching chat history:', error)
      return []
    }
  }
}
