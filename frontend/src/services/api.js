const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const GO_SEARCH_API = import.meta.env.VITE_GO_SEARCH_URL || 'http://localhost:8080'

// Anime API endpoints
export const animeAPI = {
  getAll: async (limit = 20) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime?limit=${limit}`)
      return await res.json()
    } catch (error) {
      console.error('Error fetching anime:', error)
      return []
    }
  },

  getById: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/anime/${id}`)
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
  }
}

// Chat API endpoints
export const chatAPI = {
  send: async (message, context = '') => {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          context
        })
      })
      return await res.json()
    } catch (error) {
      console.error('Error sending chat message:', error)
      return { response: 'Error connecting to chat service' }
    }
  }
}

// Embedding API
export const embeddingAPI = {
  generate: async (text) => {
    try {
      const res = await fetch(`${API_BASE}/api/embedding`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      })
      return await res.json()
    } catch (error) {
      console.error('Error generating embedding:', error)
      return null
    }
  }
}

// Recommendation API
export const recommendAPI = {
  getByGenre: async (genre, limit = 10) => {
    try {
      const res = await fetch(`${API_BASE}/api/recommend?preference=${encodeURIComponent(genre)}&limit=${limit}`)
      return await res.json()
    } catch (error) {
      console.error('Error getting recommendations:', error)
      return []
    }
  }
}
