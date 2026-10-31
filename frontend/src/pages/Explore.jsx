import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './Explore.css'
import { searchAPI, animeAPI } from '../services/api'

// Empty default - will be populated from API
const defaultResults = []

export default function Explore() {
  const [allResults, setAllResults] = useState(defaultResults) // All unfiltered results
  const [results, setResults] = useState(defaultResults)  // Filtered results
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [openPopup, setOpenPopup] = useState(null)
  const [filters, setFilters] = useState({
    ratingMin: 0,
    ratingMax: 10,
    genres: [],
    yearMin: 1970,
    yearMax: 2026,
    studio: 'Any Studio'
  })

  // Load random anime on mount
  useEffect(() => {
    const loadRandomAnime = async () => {
      setLoading(true)
      try {
        const data = await animeAPI.getAll(100)
        if (Array.isArray(data)) {
          setAllResults(data)
          setResults(data)
        }
      } catch (error) {
        console.error('Error loading anime:', error)
      } finally {
        setLoading(false)
      }
    }
    loadRandomAnime()
  }, [])

  const handleSearch = async (query) => {
    if (!query.trim()) return

    setLoading(true)
    try {
      const data = await searchAPI.anime(query)
      if (Array.isArray(data)) {
        setAllResults(data)
        setResults(data)
        setFilters({ ratingMin: 0, ratingMax: 10, genres: [], yearMin: 1970, yearMax: 2026, studio: 'Any Studio' }) // Reset filters
        setOpenPopup(null)
      }
    } catch (error) {
      console.error('Search error:', error)
    } finally {
      setLoading(false)
    }
  }

  // Apply filters whenever filter state changes
  useEffect(() => {
    if (!allResults.length) return

    let filtered = [...allResults]

    // Filter by rating range
    filtered = filtered.filter(a =>
      a.rating >= filters.ratingMin && a.rating <= filters.ratingMax
    )

    // Filter by genres (if any selected)
    if (filters.genres.length > 0) {
      filtered = filtered.filter(a =>
        a.genres && a.genres.some(g =>
          filters.genres.some(fg => g.toLowerCase().includes(fg.toLowerCase()))
        )
      )
    }

    // Filter by year range
    filtered = filtered.filter(a =>
      a.year >= filters.yearMin && a.year <= filters.yearMax
    )

    // Filter by studio
    if (filters.studio !== 'Any Studio') {
      filtered = filtered.filter(a =>
        a.studios && a.studios.some(s =>
          s.toLowerCase().includes(filters.studio.toLowerCase())
        )
      )
    }

    setResults(filtered)
  }, [filters, allResults])

  return (
    <div className="explore-wrapper">
      <div className="explore-header">
        <h2 className="explore-title">Anime Explorer</h2>
      </div>

      <div className="filter-bar">
        <button
          className={`filter-tab ${filters.ratingMin > 0 || filters.ratingMax < 10 ? 'active' : ''}`}
          onClick={() => setOpenPopup(openPopup === 'rating' ? null : 'rating')}
        >
          ⭐ Rating
        </button>
        <button
          className={`filter-tab ${filters.genres.length > 0 ? 'active' : ''}`}
          onClick={() => setOpenPopup(openPopup === 'genre' ? null : 'genre')}
        >
          🎬 Genre
        </button>
        <button
          className={`filter-tab ${filters.yearMin > 1970 || filters.yearMax < 2026 ? 'active' : ''}`}
          onClick={() => setOpenPopup(openPopup === 'year' ? null : 'year')}
        >
          📅 Year
        </button>
        <button
          className={`filter-tab ${filters.studio !== 'Any Studio' ? 'active' : ''}`}
          onClick={() => setOpenPopup(openPopup === 'studio' ? null : 'studio')}
        >
          🎨 Studio
        </button>

        {/* Rating Popup */}
        {openPopup === 'rating' && (
          <div className="filter-popup open" style={{left: '0px', top: '50px'}}>
            <div className="popup-title">Rating Range</div>
            <div className="range-inputs">
              <input
                type="number"
                className="range-input"
                min="0"
                max="10"
                step="0.5"
                value={filters.ratingMin}
                onChange={(e) => setFilters({...filters, ratingMin: parseFloat(e.target.value)})}
                placeholder="From"
              />
              <span style={{color: 'var(--text-muted)'}}>to</span>
              <input
                type="number"
                className="range-input"
                min="0"
                max="10"
                step="0.5"
                value={filters.ratingMax}
                onChange={(e) => setFilters({...filters, ratingMax: parseFloat(e.target.value)})}
                placeholder="To"
              />
            </div>
          </div>
        )}

        {/* Genre Popup */}
        {openPopup === 'genre' && (
          <div className="filter-popup open" style={{left: '110px', top: '50px'}}>
            <div className="popup-title">Select Genres</div>
            <div className="genre-list">
              {['Action', 'Romance', 'Comedy', 'Dark Fantasy', 'Sci-Fi', 'Drama'].map(g => (
                <div key={g} className="genre-item">
                  <input
                    type="checkbox"
                    id={`g-${g}`}
                    checked={filters.genres.includes(g)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFilters({...filters, genres: [...filters.genres, g]})
                      } else {
                        setFilters({...filters, genres: filters.genres.filter(x => x !== g)})
                      }
                    }}
                  />
                  <label htmlFor={`g-${g}`}>{g}</label>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Year Popup */}
        {openPopup === 'year' && (
          <div className="filter-popup open" style={{left: '220px', top: '50px'}}>
            <div className="popup-title">Year Range</div>
            <div className="range-inputs">
              <input
                type="number"
                className="range-input"
                min="1970"
                max="2026"
                value={filters.yearMin}
                onChange={(e) => setFilters({...filters, yearMin: parseInt(e.target.value)})}
                placeholder="From"
              />
              <span style={{color: 'var(--text-muted)'}}>to</span>
              <input
                type="number"
                className="range-input"
                min="1970"
                max="2026"
                value={filters.yearMax}
                onChange={(e) => setFilters({...filters, yearMax: parseInt(e.target.value)})}
                placeholder="To"
              />
            </div>
          </div>
        )}

        {/* Studio Popup */}
        {openPopup === 'studio' && (
          <div className="filter-popup open" style={{left: '330px', top: '50px'}}>
            <div className="popup-title">Select Studio</div>
            <select
              className="studio-dropdown"
              value={filters.studio}
              onChange={(e) => setFilters({...filters, studio: e.target.value})}
            >
              <option>Any Studio</option>
              <option>MAPPA</option>
              <option>Madhouse</option>
              <option>Studio Ghibli</option>
              <option>Wit Studio</option>
              <option>Kyoto Animation</option>
              <option>A-1 Pictures</option>
              <option>ufotable</option>
            </select>
          </div>
        )}
      </div>

      <div className="results-header">
        <div className="results-count">{results.length} Results Found</div>
        <div className="results-page-info">Page 1 of 10 (5 per page)</div>
      </div>

      <div className="results-list">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            Loading results...
          </div>
        ) : results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
            No results found. Try a different search.
          </div>
        ) : results.slice(0, 5).map(result => (
          <Link key={result.id} to={`/title/${result.id}`} style={{ textDecoration: 'none' }}>
            <div className="result-item">
              <div className="result-item-poster" style={{ backgroundImage: `url(${result.cover_image})` }}></div>
              <div className="result-item-content">
                <span className="result-item-badge rating">{result.rating}★</span>
                <div className="result-item-header">
                  <h3 className="result-item-title">{result.name || result.title}</h3>
                  <div className="result-item-meta">
                    <span className="result-item-badge">{result.year}</span>
                    <span className="result-item-badge">{result.studios?.[0] || 'N/A'}</span>
                  </div>
                  <div className="info-tags">
                    {result.genres?.map(genre => (
                      <span key={genre} className="tag">{genre}</span>
                    ))}
                  </div>
                </div>
                <p className="result-item-synopsis">{result.synopsis || 'No description available'}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="pagination">
        <button className="pagination-btn" disabled>← Previous</button>
        <span className="pagination-info">Page 1 of 10</span>
        <button className="pagination-btn">Next →</button>
      </div>
    </div>
  )
}
