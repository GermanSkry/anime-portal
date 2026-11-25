import { useState, useEffect, useRef, forwardRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import './Title.css'
import { animeAPI } from '../services/api'
import { track } from '../services/analytics'
import ChatModal from '../components/ChatModal'

// Genre, year and studio open Browse with that filter already applied.
// They used to point at /explore, which is the graph now and ignores the state.
const navigateToExplore = (navigate, filterType, filterValue) => {
  navigate('/browse', {
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
  const [franchise, setFranchise] = useState([])
  const stripRef = useRef(null)
  const currentRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [chatOpen, setChatOpen] = useState(false)

  useEffect(() => {
    const loadTitle = async () => {
      if (!id) {
        setLoading(false)
        return
      }

      try {
        setFranchise([])
        setSimilar([])
        const data = await animeAPI.getById(id)
        if (data) {
          setTitle(data)

          // the rest of the franchise, then what it is closest to by plot
          const [franchiseData, similarData] = await Promise.all([
            animeAPI.getFranchise(id),
            animeAPI.getSimilar(id),
          ])
          setFranchise(franchiseData)
          setSimilar(similarData)
        }
      } catch (error) {
        console.error('Error loading title:', error)
      } finally {
        setLoading(false)
      }
    }

    loadTitle()
  }, [id])

  // The strip opens on the title you are reading, not on the oldest season.
  // Setting scrollLeft rather than scrollIntoView, which also scrolls the page
  // — it was opening the page 700px down, at the strip.
  useEffect(() => {
    const strip = stripRef.current
    const card = currentRef.current
    if (!strip || !card) return
    strip.scrollLeft = card.offsetLeft - strip.offsetLeft
      - (strip.clientWidth - card.clientWidth) / 2
  }, [franchise])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>Loading...</div>
  }

  if (!title) {
    return <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
      Could not load this anime. It may not exist, or the server is unavailable.
    </div>
  }

  // The whole run in watch order, with this title in its place, so the strip
  // shows where you are rather than starting from the oldest every time.
  //
  // The filter is not belt and braces. Moving between two titles of one
  // franchise, `id` changes a render before the new list arrives, so the old
  // list still holds the title that is now current — two children with the
  // same key, which React renders twice and then leaves in the DOM after the
  // list settles. That was the season appearing twice.
  const current = Number(id)
  const run = [...franchise.filter(a => a.id !== current), { ...title, id: current, current: true }]
    .sort((a, b) => (a.year || 0) - (b.year || 0) || a.id - b.id)

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

      {franchise.length > 0 && (
        <div className="similar-section">
          <div className="similar-title">🎞️ The franchise</div>
          <div className="strip-wrap">
            {run.length > 4 && (
              <button className="strip-arrow left" aria-label="Earlier"
                      onClick={() => scrollStrip(stripRef, -1)}>‹</button>
            )}
            <div className="franchise-strip" ref={stripRef}>
              {run.map(anime => (
                <FranchiseCard
                  key={anime.id}
                  anime={anime}
                  from={id}
                  ref={anime.current ? currentRef : null}
                />
              ))}
            </div>
            {run.length > 4 && (
              <button className="strip-arrow right" aria-label="Later"
                      onClick={() => scrollStrip(stripRef, 1)}>›</button>
            )}
          </div>
        </div>
      )}

      <div className="similar-section">
        <div className="similar-title">📽️ Similar Titles</div>
        <div className="similar-grid">
          {similar.map(anime => (
            <Link
              key={anime.id}
              to={`/title/${anime.id}`}
              style={{ textDecoration: 'none' }}
              onClick={() => track('anime_opened', { source: 'similar', anime_id: anime.id, from_anime_id: id })}
            >
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

// one card width plus its gap, so a press lands on a card rather than between
function scrollStrip(ref, direction) {
  const strip = ref.current
  if (!strip) return
  strip.scrollBy({ left: direction * (strip.clientWidth * 0.8), behavior: 'smooth' })
}

const FranchiseCard = forwardRef(function FranchiseCard({ anime, from }, ref) {
  const body = (
    <div className={`similar-card ${anime.current ? 'current' : ''}`}>
      <div className="similar-poster" style={{ backgroundImage: `url(${anime.cover_image})` }}>
        {anime.current && <span className="strip-you-are-here">You are here</span>}
      </div>
      <div className="similar-info">
        <div className="similar-name">{anime.title_english || anime.name}</div>
        <div className="similar-meta">{anime.year} • {anime.studios?.[0] || 'N/A'}</div>
        <div className="similar-rating">⭐ {anime.rating}</div>
      </div>
    </div>
  )
  return (
    <div className="strip-item" ref={ref}>
      {anime.current ? body : (
        <Link
          to={`/title/${anime.id}`}
          style={{ textDecoration: 'none' }}
          onClick={() => track('anime_opened', { source: 'franchise', anime_id: anime.id, from_anime_id: from })}
        >
          {body}
        </Link>
      )}
    </div>
  )
})
