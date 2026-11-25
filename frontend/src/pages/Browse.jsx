import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Browse.css'
import { animeAPI, searchAPI } from '../services/api'
import { track } from '../services/analytics'

const defaultAnimeData = {
  best: [],
  new: [],
  action: [],
  drama: [],
  psychological: [],
}

// Announced titles carry a future year, so the ceiling has to move with the
// calendar. Hardcoded at 2026 it was already hiding 14 titles dated 2027.
const MAX_YEAR = new Date().getFullYear() + 2

const DEFAULT_FILTERS = {
  ratingMin: 0,
  ratingMax: 10,
  genres: [],
  yearMin: 1970,
  yearMax: MAX_YEAR,
  studio: 'Any Studio',
}

const GENRES = [
  'Action', 'Drama', 'Comedy', 'Fantasy', 'Supernatural', 'Adventure',
  'Romance', 'Psychological', 'Slice of Life', 'Mystery', 'Sci-Fi',
  'Thriller', 'Horror', 'Ecchi', 'Sports', 'Mecha',
]

const STUDIOS = [
  'Any Studio', 'bones', 'A-1 Pictures', 'MAPPA', 'MADHOUSE', 'J.C.STAFF',
  'Production I.G', 'WIT STUDIO', 'CloverWorks', 'ufotable', 'Kyoto Animation',
  'WHITE FOX', 'Studio Pierrot',
]

const PAGE = 24

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

function filtersFrom(state) {
  const { type, value } = state?.applyFilter || {}
  if (!value) return DEFAULT_FILTERS
  if (type === 'genre') return { ...DEFAULT_FILTERS, genres: [value] }
  if (type === 'year') return { ...DEFAULT_FILTERS, yearMin: value, yearMax: value }
  if (type === 'studio') return { ...DEFAULT_FILTERS, studio: value }
  return DEFAULT_FILTERS
}

export default function Browse() {
  const location = useLocation()
  const [animeData, setAnimeData] = useState(defaultAnimeData)
  const [searchQuery, setSearchQuery] = useState('')
  // A genre, year or studio clicked on a title page navigates here with the
  // filter in route state, which arrives on mount — so it is the initial
  // value, not an effect that re-renders to apply it.
  const [filters, setFilters] = useState(() => filtersFrom(location.state))
  const [openPopup, setOpenPopup] = useState(null)
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [more, setMore] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadAnime = async () => {
      try {
        // Browse's rows are a curated view — four cards each — so they draw
        // from the top 100 by rating rather than the whole catalogue. The
        // search and the filters below go to the server instead.
        const data = await animeAPI.getAll(100)
        if (data && data.length > 0) {
          setAnimeData({
            best: [...data].sort((a, b) => (b.rating || 0) - (a.rating || 0)).slice(0, 4),
            new: [...data].sort((a, b) => (b.year || 0) - (a.year || 0)).slice(0, 4),
            action: data.filter(a => a.genres?.includes('Action')).slice(0, 4),
            drama: data.filter(a => a.genres?.includes('Drama')).slice(0, 4),
            psychological: data.filter(a => a.genres?.includes('Psychological')).slice(0, 4),
          })
        }
      } catch (error) {
        console.error('Error loading anime:', error)
      } finally {
        setLoading(false)
      }
    }
    loadAnime()
  }, [])

  // one source of truth for "this filter is doing something", used by the tab
  // highlight, the badges and the reset button below
  const ratingFiltered = filters.ratingMin > DEFAULT_FILTERS.ratingMin
    || filters.ratingMax < DEFAULT_FILTERS.ratingMax
  const genreFiltered = filters.genres.length > 0
  const yearFiltered = filters.yearMin > DEFAULT_FILTERS.yearMin
    || filters.yearMax < DEFAULT_FILTERS.yearMax
  const studioFiltered = filters.studio !== DEFAULT_FILTERS.studio
  const hasFilters = ratingFiltered || genreFiltered || yearFiltered || studioFiltered
  const query = searchQuery.trim()
  const active = query.length > 0 || hasFilters

  // results outlive a cleared search by one render, so read them only when
  // something is actually being searched for
  const shown = active ? results : []

  const params = {
    q: query || undefined,
    genres: genreFiltered ? filters.genres : undefined,
    ratingMin: ratingFiltered ? filters.ratingMin : undefined,
    ratingMax: ratingFiltered ? filters.ratingMax : undefined,
    yearMin: yearFiltered ? filters.yearMin : undefined,
    yearMax: yearFiltered ? filters.yearMax : undefined,
    studio: studioFiltered ? filters.studio : undefined,
  }
  // the effect below depends on the values, not on a fresh object each render
  const key = JSON.stringify(params)

  // One request for the text and the filters together: /api/search takes both,
  // so nothing is sifted in the browser and the whole catalogue is reachable.
  useEffect(() => {
    if (!active) return
    const timer = setTimeout(async () => {
      setSearching(true)
      const data = await searchAPI.catalogue({ ...JSON.parse(key), limit: PAGE })
      setResults(data)
      setMore(data.length === PAGE)
      setSearching(false)
    }, 250)   // a keystroke a request would be one per letter typed
    return () => clearTimeout(timer)
  }, [key, active])

  const loadMore = async () => {
    const data = await searchAPI.catalogue({ ...params, limit: PAGE, offset: results.length })
    setResults(prev => [...prev, ...data])
    setMore(data.length === PAGE)
  }

  // one event the first time each filter turns on, so a dragged slider does not
  // produce a hundred of them. Answers "which filters do people actually use".
  const previouslyActive = useRef({})
  useEffect(() => {
    const on = {
      rating: ratingFiltered, genre: genreFiltered,
      year: yearFiltered, studio: studioFiltered,
    }
    Object.entries(on).forEach(([name, isOn]) => {
      if (isOn && !previouslyActive.current[name]) track('filter_applied', { filter: name })
    })
    previouslyActive.current = on
  }, [ratingFiltered, genreFiltered, yearFiltered, studioFiltered])

  const clearAll = () => {
    track('filters_cleared', { result_count: results.length })
    setFilters(DEFAULT_FILTERS)
    setSearchQuery('')
    setOpenPopup(null)
  }

  return (
    <div className="browse-wrapper">
      <div className="browse-hero">
        <h1>Discover Anime</h1>
        <div className="search-bar">
          <input
            type="text"
            className="search-input"
            placeholder="Search by title or plot…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
          {active && (
            <button className="search-btn" onClick={clearAll}>Clear</button>
          )}
        </div>

        <div className="filter-bar">
          {/* the tabs scroll, the bar does not: overflow on the bar would clip
              the popups, which are absolutely positioned against it */}
          <div className="filter-tabs">
            <button
              className={`filter-tab ${ratingFiltered ? 'active' : ''}`}
              onClick={() => setOpenPopup(openPopup === 'rating' ? null : 'rating')}
            >
              ⭐ Rating
            </button>
            <button
              className={`filter-tab ${genreFiltered ? 'active' : ''}`}
              onClick={() => setOpenPopup(openPopup === 'genre' ? null : 'genre')}
            >
              🎬 Genre
            </button>
            <button
              className={`filter-tab ${yearFiltered ? 'active' : ''}`}
              onClick={() => setOpenPopup(openPopup === 'year' ? null : 'year')}
            >
              📅 Year
            </button>
            <button
              className={`filter-tab ${studioFiltered ? 'active' : ''}`}
              onClick={() => setOpenPopup(openPopup === 'studio' ? null : 'studio')}
            >
              🎨 Studio
            </button>
          </div>

          {openPopup === 'rating' && (
            <div className="filter-popup open">
              <div className="popup-title">Rating Range</div>
              <div className="range-inputs">
                <input
                  type="number" className="range-input" min="0" max="10" step="0.5"
                  value={filters.ratingMin} placeholder="From"
                  onChange={e => setFilters({ ...filters, ratingMin: parseFloat(e.target.value) || 0 })}
                />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input
                  type="number" className="range-input" min="0" max="10" step="0.5"
                  value={filters.ratingMax} placeholder="To"
                  onChange={e => setFilters({ ...filters, ratingMax: parseFloat(e.target.value) || 10 })}
                />
              </div>
            </div>
          )}

          {openPopup === 'genre' && (
            <div className="filter-popup open">
              <div className="popup-title">Select Genres</div>
              <div className="genre-list">
                {GENRES.map(g => (
                  <div key={g} className="genre-item">
                    <input
                      type="checkbox"
                      id={`g-${g}`}
                      checked={filters.genres.includes(g)}
                      onChange={e => setFilters({
                        ...filters,
                        genres: e.target.checked
                          ? [...filters.genres, g]
                          : filters.genres.filter(x => x !== g),
                      })}
                    />
                    <label htmlFor={`g-${g}`}>{g}</label>
                  </div>
                ))}
              </div>
            </div>
          )}

          {openPopup === 'year' && (
            <div className="filter-popup open">
              <div className="popup-title">Year Range</div>
              <div className="range-inputs">
                <input
                  type="number" className="range-input" min="1970" max={MAX_YEAR}
                  value={filters.yearMin} placeholder="From"
                  onChange={e => setFilters({ ...filters, yearMin: parseInt(e.target.value) || DEFAULT_FILTERS.yearMin })}
                />
                <span style={{ color: 'var(--text-muted)' }}>to</span>
                <input
                  type="number" className="range-input" min="1970" max={MAX_YEAR}
                  value={filters.yearMax} placeholder="To"
                  onChange={e => setFilters({ ...filters, yearMax: parseInt(e.target.value) || MAX_YEAR })}
                />
              </div>
            </div>
          )}

          {openPopup === 'studio' && (
            <div className="filter-popup open">
              <div className="popup-title">Select Studio</div>
              <select
                className="studio-dropdown"
                value={filters.studio}
                onChange={e => setFilters({ ...filters, studio: e.target.value })}
              >
                {STUDIOS.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
          )}
        </div>

        {hasFilters && (
          <div className="active-filters">
            {ratingFiltered && (
              <div className="filter-badge">⭐ Rating: {filters.ratingMin}-{filters.ratingMax}</div>
            )}
            {filters.genres.map(genre => (
              <div key={genre} className="filter-badge">🎬 {genre}</div>
            ))}
            {yearFiltered && (
              <div className="filter-badge">📅 Year: {filters.yearMin}-{filters.yearMax}</div>
            )}
            {studioFiltered && <div className="filter-badge">🎨 {filters.studio}</div>}
            <button className="clear-filters-btn" onClick={clearAll}>✕ Clear filters</button>
          </div>
        )}
      </div>

      {active ? (
        <div className="browse-section">
          <h2 className="section-title">
            {searching ? 'Searching…'
              : `${shown.length}${more ? '+' : ''} ${shown.length === 1 ? 'result' : 'results'}`}
            {query && ` for “${query}”`}
          </h2>
          {!searching && shown.length === 0 ? (
            <p className="browse-none">
              Nothing matches. Widen the rating or year range, or drop a genre.
            </p>
          ) : (
            <>
              <div className="browse-grid">
                {shown.map(anime => (
                  <AnimeCard key={anime.id} anime={anime} section="search" />
                ))}
              </div>
              {more && (
                <button className="browse-more" onClick={loadMore}>Show more</button>
              )}
            </>
          )}
        </div>
      ) : loading ? (
        <div className="browse-loading">Loading…</div>
      ) : (
        Object.entries(animeData).map(([section, animes]) => {
          const sectionGenre = {
            action: 'Action', drama: 'Drama', psychological: 'Psychological',
          }[section]
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
                  <AnimeCard key={anime.id} anime={anime} section={section}
                             sectionGenre={sectionGenre} />
                ))}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}

function AnimeCard({ anime, section, sectionGenre }) {
  return (
    <Link
      to={`/title/${anime.id}`}
      style={{ textDecoration: 'none' }}
      onClick={() => track('anime_opened', { source: 'browse', anime_id: anime.id, section })}
    >
      <div className="browse-card">
        <div className="browse-poster" style={{ backgroundImage: `url(${anime.cover_image})` }}></div>
        <div className="browse-badge">{anime.rating}</div>
        <div className="browse-info">
          <div className="browse-title">{anime.title_english || anime.name}</div>
          <div className="browse-meta">{anime.year}</div>
          <div className="browse-genres">
            {getGenresForSection(anime, sectionGenre).slice(0, 3).join(', ') || 'N/A'}
          </div>
        </div>
      </div>
    </Link>
  )
}
