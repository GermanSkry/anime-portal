import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './Browse.css'
import { animeAPI, recommendAPI } from '../services/api'

const defaultAnimeData = {
  best: [
    { id: 1, name: 'Steins;Gate', year: '2011', genre: 'Sci-Fi', rating: '9.0' },
    { id: 2, name: 'Attack on Titan', year: '2013', genre: 'Action', rating: '8.9' },
    { id: 3, name: 'Vinland Saga', year: '2019', genre: 'Historical', rating: '8.8' },
    { id: 4, name: 'Natsume Yuujinchou', year: '2008', genre: 'Supernatural', rating: '8.7' },
  ],
  new: [
    { id: 5, name: 'Jujutsu Kaisen S4', year: '2026', genre: 'Action', rating: '8.6' },
    { id: 6, name: 'Wind Breaker', year: '2026', genre: 'School', rating: '8.3' },
    { id: 7, name: 'Oshi no Ko S2', year: '2025', genre: 'Drama', rating: '8.5' },
    { id: 8, name: 'Solo Leveling', year: '2024', genre: 'Action', rating: '8.4' },
  ],
  action: [
    { id: 9, name: 'Demon Slayer', year: '2019', genre: 'Action', rating: '8.7' },
    { id: 10, name: 'My Hero Academia', year: '2016', genre: 'Action', rating: '8.4' },
    { id: 11, name: 'Mob Psycho 100', year: '2016', genre: 'Comedy', rating: '8.4' },
    { id: 12, name: 'Chainsaw Man', year: '2022', genre: 'Action', rating: '8.6' },
  ],
}

export default function Browse() {
  const [animeData, setAnimeData] = useState(defaultAnimeData)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadAnime = async () => {
      try {
        console.log('Fetching anime from backend...')
        const data = await animeAPI.getAll(12)
        console.log('Received data:', data)
        if (data && data.length > 0) {
          console.log(`Got ${data.length} anime, creating sections`)
          setAnimeData({
            best: data.slice(0, 4),
            new: data.slice(4, 8),
            action: data.slice(8, 12),
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

      {Object.entries(animeData).map(([section, animes]) => (
        <div key={section} className="browse-section">
          <h2 className="section-title">
            {section === 'best' && '⭐ Best (Highest Rated)'}
            {section === 'new' && '🆕 New (Recent Releases)'}
            {section === 'action' && '⚔️ Action'}
          </h2>
          <div className="browse-grid">
            {animes.map(anime => (
              <Link key={anime.id} to={`/title/${anime.id}`} style={{ textDecoration: 'none' }}>
                <div className="browse-card">
                  <div className="browse-poster" style={{ backgroundImage: `url(${anime.cover_image})` }}></div>
                  <div className="browse-badge">{anime.rating}</div>
                  <div className="browse-info">
                    <div className="browse-title">{anime.name}</div>
                    <div className="browse-meta">{anime.year} • {anime.genres?.[0] || 'N/A'}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
