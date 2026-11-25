import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import './ExploreGraph.css'
import { fetchGraph, nearest, neighbourhood, seedView } from '../services/graph'
import { track } from '../services/analytics'

// three.js and the canvas renderer are heavy; Chat and Browse should not pay
// for them, so the renderer only loads when this route does
const ForceGraph2D = lazy(() => import('react-force-graph-2d'))

// Colour is genre, not franchise. 371 franchises cannot have 371 colours, so
// the old scheme gave two unrelated shows the same red and said nothing; genre
// repeats on purpose, and a red cluster means something. The selected title's
// own franchise turns white on top, which is the one grouping worth seeing.
const GENRE_COLOURS = {
  Comedy: '#facc15',
  'Action & adventure': '#ef4444',
  'Sci-fi & mecha': '#38bdf8',
  Mystery: '#c084fc',
  'Sports & music': '#fb923c',
  Romance: '#f472b6',
  Fantasy: '#22c55e',
  'Horror & thriller': '#6366f1',
}
// A title carries four or five genres and this picks one, so the order is the
// whole design. Rare, defining genres come first; the mood tags a show merely
// *also* is — Psychological, Supernatural, Drama, Slice of Life — come last.
// Checked against the catalogue: Naruto and Demon Slayer land in action,
// Death Note in mystery, Steins;Gate in sci-fi, Kaguya in comedy, and no
// group takes less than 5% of the 2,500.
const GENRE_ORDER = [
  ['Mahou Shoujo', 'Fantasy'], ['Music', 'Sports & music'], ['Mecha', 'Sci-fi & mecha'],
  ['Sports', 'Sports & music'], ['Horror', 'Horror & thriller'], ['Mystery', 'Mystery'],
  ['Sci-Fi', 'Sci-fi & mecha'], ['Adventure', 'Action & adventure'], ['Comedy', 'Comedy'],
  ['Romance', 'Romance'], ['Fantasy', 'Fantasy'], ['Thriller', 'Horror & thriller'],
  ['Action', 'Action & adventure'], ['Psychological', 'Mystery'], ['Ecchi', 'Romance'],
  ['Supernatural', 'Fantasy'],
]
// drama and slice of life alone, which is 1% of the catalogue
const UNGENRED = '#64748b'
const FRANCHISE = '#ffffff'

const groupOf = node =>
  GENRE_ORDER.find(([genre]) => node.genres?.includes(genre))?.[1] || null

// litFranchise is the selected title's, and only when it has siblings here.
const colourFor = (node, litFranchise) =>
  (node.franchise === litFranchise ? FRANCHISE : GENRE_COLOURS[groupOf(node)] || UNGENRED)

// Rating drives size, but gently: the 8.5+ tier spans 8.5 to 9.1, so anything
// steeper turns a 0.6 point spread into wildly different blobs.
const radiusOf = node => 3 + Math.max(0, (node.rating || 6) - 6) * 1.1

export default function ExploreGraph() {
  const navigate = useNavigate()
  const wrapRef = useRef(null)
  const graphRef = useRef(null)
  const [graph, setGraph] = useState(null)
  const [view, setView] = useState(null)
  const [selected, setSelected] = useState(null)
  const [centre, setCentre] = useState(null)
  const [hovered, setHovered] = useState(null)
  // the renderer's click handler does not carry the native event's detail
  // count, so a double click is two clicks on one node, timed here
  const lastClick = useRef({ id: null, at: 0 })
  const [trail, setTrail] = useState([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState(null)
  const [size, setSize] = useState({ width: 800, height: 560 })

  useEffect(() => {
    fetchGraph()
      .then(g => { setGraph(g); setView(seedView(g)) })
      .catch(e => setError(e.message))
  }, [])

  // the canvas needs explicit pixels, so follow the container
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ width, height: Math.max(height, 360) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const recentre = useCallback((node) => {
    if (!graph) return
    setView(neighbourhood(graph, node.id))
    setCentre(node.id)
    setSelected(node)
    setTrail(t => (t.at(-1)?.id === node.id ? t : [...t, node].slice(-6)))
    track('graph_recentred', { anime_id: node.id, from_seed: centre === null })
  }, [graph, centre])

  const backToSeed = () => {
    setView(seedView(graph)); setCentre(null); setSelected(null); setTrail([])
    track('graph_reset', {})
  }

  if (error) {
    return <div className="graph-message">Could not load the graph: {error}</div>
  }
  if (!graph || !view) {
    return <div className="graph-message">Loading 2,500 anime…</div>
  }

  const q = query.trim().toLowerCase()
  // 2,500 names in memory, so no request and no debounce; best rated first,
  // because a search for "gundam" should not open on a picture drama
  const matches = q.length < 2 ? [] : [...graph.nodes.values()]
    .filter(n => n.name?.toLowerCase().includes(q))
    .sort((a, b) => (b.rating || 0) - (a.rating || 0))
    .slice(0, 8)

  const related = selected ? nearest(graph, selected.id, 5) : []
  // white is reserved for the franchise of whatever is selected, so it only
  // means something when that franchise has more than one title on screen
  const litFranchise =
    selected && view.nodes.filter(n => n.franchise === selected.franchise).length > 1
      ? selected.franchise
      : null
  // Only the picked title's five closest are drawn in pink. Marking every
  // node's jump turned a useful signal into wallpaper.
  const litLinks = new Set(
    related.map(r => (selected.id < r.id ? `${selected.id}:${r.id}` : `${r.id}:${selected.id}`))
  )
  const isLit = l => {
    const a = l.source?.id ?? l.source
    const b = l.target?.id ?? l.target
    return litLinks.has(a < b ? `${a}:${b}` : `${b}:${a}`)
  }

  return (
    <div className="graph-page">
      <div className="graph-header">
        <div className="graph-search">
          <input
            type="search"
            value={query}
            placeholder="Start from a title…"
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && matches[0]) { recentre(matches[0]); setQuery('') }
              if (e.key === 'Escape') setQuery('')
            }}
          />
          {matches.length > 0 && (
            <ul className="search-results">
              {matches.map(n => (
                <li key={n.id}>
                  <button onClick={() => { recentre(n); setQuery('') }}>
                    <span className="search-name">{n.name}</span>
                    <span className="search-meta">{n.year} · {n.rating}★</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="graph-breadcrumbs">
          <button className="crumb" onClick={backToSeed} disabled={!centre}>
            ★ Top rated
          </button>
          {trail.map(n => (
            <button key={n.id} className={`crumb ${n.id === centre ? 'current' : ''}`}
                    onClick={() => recentre(n)}>
              {(n.name || '').slice(0, 22)}
            </button>
          ))}
        </div>
      </div>

      <div className="graph-layout">
        <div className="graph-canvas" ref={wrapRef}>
          <Suspense fallback={<div className="graph-message">Loading the renderer…</div>}>
            <ForceGraph2D
              ref={graphRef}
              width={size.width}
              height={size.height}
              graphData={view}
              backgroundColor="rgba(0,0,0,0)"
              nodeId="id"
              nodeRelSize={1}
              nodeVal={n => radiusOf(n) ** 2}
              linkColor={l => (isLit(l)
                ? 'rgba(236,72,153,0.85)'
                : `rgba(148,163,184,${0.08 + (l.w || 0) * 0.35})`)}
              linkWidth={l => (isLit(l) ? 1.8 : 0.3 + (l.w || 0) * 1.2)}
              d3VelocityDecay={0.3}
              cooldownTicks={120}
              nodeLabel={() => ''}
              onNodeHover={n => setHovered(n?.id ?? null)}
              onNodeClick={n => {
                const now = Date.now()
                const { id, at } = lastClick.current
                lastClick.current = { id: n.id, at: now }
                if (id === n.id && now - at < 400) recentre(n)
                else setSelected(n)
              }}
              onNodeRightClick={recentre}
              onEngineStop={() => graphRef.current?.zoomToFit(400, 50)}
              nodeCanvasObject={(node, ctx, scale) => {
                const r = radiusOf(node)
                const isCentre = node.id === centre
                const isPicked = node.id === selected?.id
                ctx.beginPath()
                ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
                ctx.fillStyle = colourFor(node, litFranchise)
                ctx.fill()
                if (isCentre || isPicked) {
                  ctx.lineWidth = 2 / scale
                  ctx.strokeStyle = node.franchise === litFranchise
                    ? '#0a0a0a'            // a white ring on a white node is nothing
                    : isCentre ? '#ffffff' : 'rgba(255,255,255,0.7)'
                  ctx.stroke()
                }
                // At fit-zoom 120 labels collide into mush, so the map shows shape
                // and colour, and names appear on hover or once you zoom in.
                if (scale > 2.2 || isCentre || isPicked || node.id === hovered) {
                  const label = node.name.length > 26 ? node.name.slice(0, 25) + '…' : node.name
                  ctx.font = `${Math.max(3, 11 / scale)}px -apple-system, sans-serif`
                  ctx.textAlign = 'center'
                  ctx.textBaseline = 'top'
                  const y = node.y + r + 2 / scale
                  const w = ctx.measureText(label).width
                  ctx.fillStyle = 'rgba(10,10,10,0.72)'
                  ctx.fillRect(node.x - w / 2 - 1, y - 0.5, w + 2, 11 / scale)
                  ctx.fillStyle = 'rgba(255,255,255,0.92)'
                  ctx.fillText(label, node.x, y)
                }
              }}
              nodePointerAreaPaint={(node, colour, ctx) => {
                ctx.fillStyle = colour
                ctx.beginPath()
                ctx.arc(node.x, node.y, radiusOf(node) + 2, 0, 2 * Math.PI)
                ctx.fill()
              }}
            />
          </Suspense>
          <div className="graph-hint">
            {view.nodes.length} anime · hover to name · click to inspect ·
            double-click to travel
          </div>
        </div>

        <aside className="graph-panel">
          {selected ? (
            <>
              {selected.cover && (
                <div className="panel-cover" style={{ backgroundImage: `url(${selected.cover})` }} />
              )}
              <h3 className="panel-title">{selected.name}</h3>
              <div className="panel-meta">
                {selected.year} · {selected.rating}★
              </div>
              <div className="panel-genres">
                {(selected.genres || []).slice(0, 4).map(g => (
                  <span key={g} className="panel-genre">{g}</span>
                ))}
              </div>

              <div className="panel-section">Closest by plot</div>
              {related.map(r => (
                <button key={r.id} className="panel-related" onClick={() => recentre(r)}>
                  <span className="related-name">{r.name}</span>
                  <span className="related-score">{Math.round(r.similarity * 100)}%</span>
                </button>
              ))}

              <div className="panel-spacer" />
              <div className="panel-actions">
                <button className="panel-btn" onClick={() => recentre(selected)}>
                  Travel here
                </button>
                <button className="panel-btn ghost" onClick={() => navigate(`/title/${selected.id}`)}>
                  Full page
                </button>
              </div>
            </>
          ) : (
            <div className="panel-empty">
              <p>
                The highest rated anime, one per franchise. Pick one to see what
                it is closest to; travelling there redraws the map around it.
              </p>
              <p className="panel-legend">
                <span className="legend-genres">
                  {Object.entries(GENRE_COLOURS).map(([name, colour]) => (
                    <span key={name} className="legend-genre">
                      <span className="legend-dot" style={{ background: colour }} />
                      {name}
                    </span>
                  ))}
                </span>
                <span className="legend-dot" style={{ background: FRANCHISE }} /> the
                franchise of the title you pick
                <br />
                <span className="legend-line" /> its five closest outside that
                franchise
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
