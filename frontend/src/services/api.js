const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GO_SEARCH_API = import.meta.env.VITE_GO_SEARCH_URL || 'http://localhost:8080'

// Anime API endpoints
export const animeAPI = {
  getAll: async (limit = 20) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime?limit=${limit}`)
      const data = await res.json()
      return Array.isArray(data) ? data : []
    } catch (error) {
      console.error('Error fetching anime:', error)
      return []
    }
  },

  getById: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}`)
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
      const res = await fetch(`${API_BASE}/api/anime/year/${year}`)
      return await res.json()
    } catch (error) {
      console.error('Error fetching anime by year:', error)
      return []
    }
  },

  getRelated: async (id, limit = 4) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}/related?limit=${limit}`)
      return await res.json()
    } catch (error) {
      console.error('Error fetching related anime:', error)
      return []
    }
  },

  getSimilar: async (id, limit = 4, minRating = 6) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}/similar?limit=${limit}&min_rating=${minRating}`)
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
      const res = await fetch(`${API_BASE}/api/search/semantic?query_text=${encodeURIComponent(query)}&limit=5`)
      return await res.json()
    } catch (error) {
      console.error('Error in anime search:', error)
      return []
    }
  },

  // full-text + filter search on the Python backend; /api/search/anime is the Go service's POST route, not this one
  animeByTitle: async (query, limit = 20) => {
    try {
      const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&limit=${limit}`)
      const data = await res.json()
      // an error response is an object, and callers render this straight into a list
      return Array.isArray(data) ? data : []
    } catch (error) {
      console.error('Error in anime title search:', error)
      return []
    }
  }
}

// Chat API endpoints
export const chatAPI = {
  send: async (message, context = '', animeId = null, messageHistory = []) => {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      const res = await fetch(`${API_BASE}/api/chat/history${query}`)
      return await res.json()
    } catch (error) {
      console.error('Error fetching chat history:', error)
      return []
    }
  }
}
