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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadAnime = async () => {
      try {
        console.log('Fetching anime from backend...')
        const data = await animeAPI.getAll(100)
        console.log('Received data:', data)
        if (data && data.length > 0) {
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
  return (
    <div className="browse-wrapper">
      <div className="browse-hero">
        <h1>Discover Anime</h1>
        <div className="search-bar">
          <input type="text" className="search-input" placeholder="Search anime..." />
          <button className="search-btn">Search</button>
        </div>
      </div>

      {Object.entries(animeData).map(([section, animes]) => {
        const sectionGenreMap = {
          action: 'Action',
          drama: 'Drama',
          psychological: 'Psychological'
        }
        const sectionGenre = sectionGenreMap[section]

        return (
          <div key={section} className="browse-section">
            <h2 className="section-title">
              {section === 'best' && '⭐ Best (Highest Rated)'}
              {section === 'new' && '🆕 New (Recent)'}
              {section === 'action' && '⚔️ Action'}
              {section === 'drama' && '🎭 Drama'}
              {section === 'psychological' && '🧠 Psychological'}
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
