import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import './Title.css'
import { animeAPI } from '../services/api'

const defaultTitle = {
  id: 1,
  name: 'Attack on Titan',
  year: '2013',
  studio: 'Wit Studio',
  rating: '8.9',
  genres: ['Action', 'Dark Fantasy', 'Adventure'],
  synopsis: 'Humanity has been decimated by the sudden appearance of colossal humanoid creatures called Titans. Little is known about where they came from, but the threat is so real that the remnants of humanity had to take refuge behind a massive wall. Eren Yeager witnesses the destruction of his hometown and the death of his mother, setting him on a path of vengeance to eliminate every last Titan.'
}

export default function Title() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [title, setTitle] = useState(defaultTitle)
  const [similar, setSimilar] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadTitle = async () => {
      if (!id) {
        setLoading(false)
        return
      }

      try {
        const data = await animeAPI.getById(id)
        if (data) {
          setTitle(data)
        }
      } catch (error) {
        console.error('Error loading title:', error)
      } finally {
        setLoading(false)
      }
    }

    loadTitle()
  }, [id])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>Loading...</div>
  }

  return (
    <div className="title-page">
      <div className="title-hero">
        <h1>{title.name}</h1>
      </div>

      <div className="title-content">
        <div className="title-poster" style={{ backgroundImage: `url(${title.cover_image})` }}></div>
        <div className="title-info">
          <div className="info-badge rating">{title.rating}★</div>
          <div className="info-meta">
            <div className="info-badge">{title.year}</div>
            <div className="info-badge">{title.studios?.[0] || title.studio || 'N/A'}</div>
          </div>
          <div className="info-tags">
            {title.genres?.map(genre => (
              <span key={genre} className="tag">{genre}</span>
            ))}
          </div>
          <div className="info-section">
            <p className="info-value">{title.synopsis || title.description || 'No description available'}</p>
          </div>
        </div>
      </div>

      <div className="title-trailer">
        <div className="trailer-title">🎬 Official Trailer</div>
        <div className="trailer-video">YouTube Video Embed</div>
      </div>

      <div className="similar-section">
        <div className="similar-title">📽️ Similar Titles</div>
        <div className="similar-grid">
          {similar.map(anime => (
            <Link key={anime.id} to={`/title/${anime.id}`} style={{ textDecoration: 'none' }}>
              <div className="similar-card">
                <div className="similar-poster" style={{ backgroundImage: `url(${anime.cover_image})` }}></div>
                <div className="similar-info">
                  <div className="similar-name">{anime.name}</div>
                  <div className="similar-meta">{anime.year} • {anime.genre}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <button className="ai-chat-bubble" onClick={() => alert('Chat feature would open here')}>
        💬
      </button>
    </div>
  )
}
