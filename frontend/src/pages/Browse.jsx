import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './Browse.css'
import { animeAPI, recommendAPI } from '../services/api'

const defaultAnimeData = {
  best: [],
  new: [],
  action: [],
  drama: [],
  psychological: [],
}

// Helper to reorder genres so matching genre appears first
const getGenresForSection = (anime, sectionGenre) => {
  if (!anime.genres) return []
  if (!sectionGenre) return anime.genres

  // Put matching genre first if it exists
  const genres = anime.genres.slice()
  const idx = genres.indexOf(sectionGenre)
  if (idx > 0) {
    [genres[0], genres[idx]] = [genres[idx], genres[0]]
  }
  return genres
}

export default function Browse() {
  const [animeData, setAnimeData] = useState(defaultAnimeData)
  const [allAnime, setAllAnime] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadAnime = async () => {
      try {
        console.log('Fetching anime from backend...')
        const data = await animeAPI.getAll(100)
        console.log('Received data:', data)
        if (data && data.length > 0) {
          setAllAnime(data) // Store all anime for client-side search

          // Filter anime by genre
          const actionAnime = data.filter(a => a.genres?.includes('Action')).slice(0, 4)
          const dramaAnime = data.filter(a => a.genres?.includes('Drama')).slice(0, 4)
          const psychoAnime = data.filter(a => a.genres?.includes('Psychological')).slice(0, 4)

          // Best = top rated
          const bestAnime = [...data].sort((a, b) => (b.rating || 0) - (a.rating || 0)).slice(0, 4)

          // New = most recent
          const newAnime = [...data].sort((a, b) => (b.year || 0) - (a.year || 0)).slice(0, 4)

          console.log(`Best: ${bestAnime.length}, New: ${newAnime.length}, Action: ${actionAnime.length}, Drama: ${dramaAnime.length}, Psychological: ${psychoAnime.length}`)
          setAnimeData({
            best: bestAnime,
            new: newAnime,
            action: actionAnime,
            drama: dramaAnime,
            psychological: psychoAnime,
          })
        } else {
          console.log('No data received, using defaults')
        }
      } catch (error) {
        console.error('Error loading anime:', error)
      } finally {
        setLoading(false)
      }
    }

    loadAnime()
  }, [])

  const calculateSimilarity = (str, query) => {
    const s = str.toLowerCase()
    const q = query.toLowerCase()

    // Exact match
    if (s === q) return 100

    // Starts with query
    if (s.startsWith(q)) return 80

    // Contains query as substring
    if (s.includes(q)) return 60

    // Word boundary match (e.g., "gate" matches "Steins;Gate")
    const words = s.split(/[\s;:\-.,()]+/)
    if (words.some(w => w === q)) return 75
    if (words.some(w => w.startsWith(q))) return 65

    // Fuzzy: count matching characters in order
    let matches = 0
    let qIdx = 0
    for (let i = 0; i < s.length && qIdx < q.length; i++) {
      if (s[i] === q[qIdx]) {
        matches++
        qIdx++
      }
    }

    if (qIdx === q.length) {
      // All query chars found in order
      return Math.max(40, (matches / s.length) * 50)
    }

    return 0
  }

  const handleSearch = () => {
    if (!searchQuery.trim()) {
      // If search is empty, reset to default view
      handleClearSearch()
      return
    }

    const query = searchQuery.toLowerCase()

    // Score and filter anime
    const scored = allAnime
      .map(anime => ({
        anime,
        titleScore: calculateSimilarity(anime.title_english || anime.name || '', query),
        genreScore: anime.genres?.some(g => g.toLowerCase().includes(query)) ? 30 : 0,
        yearScore: String(anime.year).includes(query) ? 25 : 0
      }))
      .filter(item => item.titleScore > 0 || item.genreScore > 0 || item.yearScore > 0)
      .sort((a, b) => (b.titleScore + b.genreScore + b.yearScore) - (a.titleScore + a.genreScore + a.yearScore))

    const filtered = scored.map(item => item.anime)

    setAnimeData({
      best: filtered.slice(0, 8),
      new: [],
      action: [],
      drama: [],
      psychological: [],
    })
  }

  const handleClearSearch = () => {
    setSearchQuery('')
    // Reload default view
    const actionAnime = allAnime.filter(a => a.genres?.includes('Action')).slice(0, 4)
    const dramaAnime = allAnime.filter(a => a.genres?.includes('Drama')).slice(0, 4)
    const psychoAnime = allAnime.filter(a => a.genres?.includes('Psychological')).slice(0, 4)
    const bestAnime = [...allAnime].sort((a, b) => (b.rating || 0) - (a.rating || 0)).slice(0, 4)
    const newAnime = [...allAnime].sort((a, b) => (b.year || 0) - (a.year || 0)).slice(0, 4)

    setAnimeData({
      best: bestAnime,
      new: newAnime,
      action: actionAnime,
      drama: dramaAnime,
      psychological: psychoAnime,
    })
  }

  const handleInputChange = (e) => {
    const query = e.target.value
    setSearchQuery(query)

    // Auto-search as user types
    if (query.trim()) {
      // Trigger search with the new query
      const queryLower = query.toLowerCase()
      const scored = allAnime
        .map(anime => ({
          anime,
          titleScore: calculateSimilarity(anime.title_english || anime.name || '', query),
          genreScore: anime.genres?.some(g => g.toLowerCase().includes(queryLower)) ? 30 : 0,
          yearScore: String(anime.year).includes(queryLower) ? 25 : 0
        }))
        .filter(item => item.titleScore > 0 || item.genreScore > 0 || item.yearScore > 0)
        .sort((a, b) => (b.titleScore + b.genreScore + b.yearScore) - (a.titleScore + a.genreScore + a.yearScore))

      const filtered = scored.map(item => item.anime)
      setAnimeData({
        best: filtered.slice(0, 8),
        new: [],
        action: [],
        drama: [],
        psychological: [],
      })
    } else {
      // Empty query - show default view
      handleClearSearch()
    }
  }
  return (
    <div className="browse-wrapper">
      <div className="browse-hero">
        <h1>Discover Anime</h1>
        <div className="search-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Search by title, genre, or year..."
            value={searchQuery}
            onChange={handleInputChange}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          {!searchQuery && (
            <button className="search-btn" onClick={handleSearch} style={{ opacity: 0.6 }}>
              Search
            </button>
          )}
          {searchQuery && (
            <button className="search-btn" onClick={handleClearSearch} style={{ marginLeft: '8px', opacity: 0.8 }}>
              Clear
            </button>
          )}
        </div>
      </div>

      {Object.entries(animeData).map(([section, animes]) => {
        const sectionGenreMap = {
          action: 'Action',
          drama: 'Drama',
          psychological: 'Psychological'
        }
        const sectionGenre = sectionGenreMap[section]

        if (searchQuery && animes.length === 0) return null // Hide empty sections during search

        return (
          <div key={section} className="browse-section">
            <h2 className="section-title">
              {searchQuery ? `🔍 Search Results for "${searchQuery}" (${animes.length})` : (
                <>
                  {section === 'best' && '⭐ Best (Highest Rated)'}
                  {section === 'new' && '🆕 New (Recent)'}
                  {section === 'action' && '⚔️ Action'}
                  {section === 'drama' && '🎭 Drama'}
                  {section === 'psychological' && '🧠 Psychological'}
                </>
              )}
            </h2>
            <div className="browse-grid">
              {animes.map(anime => (
                <Link key={anime.id} to={`/title/${anime.id}`} style={{ textDecoration: 'none' }}>
                  <div className="browse-card">
                    <div className="browse-poster" style={{ backgroundImage: `url(${anime.cover_image})` }}></div>
                    <div className="browse-badge">{anime.rating}</div>
                    <div className="browse-info">
                      <div className="browse-title">{anime.title_english || anime.name}</div>
                      <div className="browse-meta">{anime.year}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {getGenresForSection(anime, sectionGenre).slice(0, 3).join(', ') || 'N/A'}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
