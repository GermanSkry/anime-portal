import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import './Title.css'
import { animeAPI } from '../services/api'
import ChatModal from '../components/ChatModal'

// Helper to navigate to Explore with filters
const navigateToExplore = (navigate, filterType, filterValue) => {
  navigate('/explore', {
    state: {
      applyFilter: { type: filterType, value: filterValue }
    }
  })
}

export default function Title() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [title, setTitle] = useState(null)
  const [similar, setSimilar] = useState([])
  const [loading, setLoading] = useState(true)
  const [chatOpen, setChatOpen] = useState(false)

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

          // Load similar anime
          const similarData = await animeAPI.getSimilar(id)
          if (Array.isArray(similarData)) {
            setSimilar(similarData)
          }
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

  if (!title) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
      Could not load this anime. It may not exist, or the server is unavailable.
    </div>
  }

  return (
    <div className="title-page">
      <div className="title-hero">
        <h1>{title.title_english || title.name}</h1>
      </div>

      <div className="title-content">
        <div className="title-poster" style={{ backgroundImage: `url(${title.cover_image})` }}></div>
        <div className="title-info">
          <div className="info-badge rating">{title.rating}★</div>
          <div className="info-meta">
            <div
              className="info-badge clickable"
              onClick={(e) => {
                e.stopPropagation()
                navigateToExplore(navigate, 'year', title.year)
              }}
              title="Filter by year"
            >
              {title.year}
            </div>
            <div
              className="info-badge clickable"
              onClick={(e) => {
                e.stopPropagation()
                navigateToExplore(navigate, 'studio', title.studios?.[0] || title.studio)
              }}
              title="Filter by studio"
            >
              {title.studios?.[0] || title.studio || 'N/A'}
            </div>
          </div>
          <div className="info-tags">
            {title.genres?.map(genre => (
              <span
                key={genre}
                className="tag clickable"
                onClick={(e) => {
                  e.stopPropagation()
                  navigateToExplore(navigate, 'genre', genre)
                }}
                title="Filter by genre"
              >
                {genre}
              </span>
            ))}
          </div>
          <div className="info-section">
            <p className="info-value">{title.synopsis || title.description || 'No description available'}</p>
          </div>
        </div>
      </div>

      {title.trailer_url && (
        <div className="title-trailer">
          <div className="trailer-title">🎬 Official Trailer</div>
          <iframe
            className="trailer-video"
            src={`https://www.youtube.com/embed/${new URL(title.trailer_url).searchParams.get('v')}`}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          ></iframe>
        </div>
      )}

      <div className="similar-section">
        <div className="similar-title">📽️ Similar Titles</div>
        <div className="similar-grid">
          {similar.map(anime => (
            <Link key={anime.id} to={`/title/${anime.id}`} style={{ textDecoration: 'none' }}>
              <div className="similar-card">
                <div className="similar-poster" style={{ backgroundImage: `url(${anime.cover_image})` }}></div>
                <div className="similar-info">
                  <div className="similar-name">{anime.title_english || anime.name}</div>
                  <div className="similar-meta">{anime.year} • {anime.studios?.[0] || 'N/A'}</div>
                  <div className="similar-genres">{anime.genres?.slice(0, 2).join(', ') || 'N/A'}</div>
                  <div className="similar-rating">⭐ {anime.rating}</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      <button className="ai-chat-bubble" onClick={() => setChatOpen(true)}>
        💬
      </button>

      <ChatModal isOpen={chatOpen} onClose={() => setChatOpen(false)} animeContext={title} />
    </div>
  )
}
