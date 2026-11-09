import { Link } from 'react-router-dom'

export default function MessageRenderer({ text, animeReferences = [] }) {
  if (!animeReferences || animeReferences.length === 0) {
    // Just render text with basic markdown formatting
    return (
      <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
        {text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i} style={{ color: 'var(--accent-end)' }}>{part.slice(2, -2)}</strong>
          }
          return part
        })}
      </div>
    )
  }

  // Create map of lower-case title to anime reference
  const animeMap = new Map(
    animeReferences.map(ref => [
      ref.title.toLowerCase(),
      ref
    ])
  )

  // Split by **bold** markers and process each part
  const parts = text.split(/(\*\*[^*]+\*\*)/g)

  const elements = parts.map((part, i) => {
    // Check if this is a bold marker
    if (part.startsWith('**') && part.endsWith('**')) {
      const title = part.slice(2, -2) // Remove ** markers
      const anime = animeMap.get(title.toLowerCase())

      if (anime) {
        return (
          <Link
            key={i}
            to={`/title/${anime.id}`}
            style={{
              color: 'var(--accent-end)',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            {title}
          </Link>
        )
      }

      // Anime not found, render as bold
      return (
        <strong key={i} style={{ color: 'var(--accent-end)' }}>
          {title}
        </strong>
      )
    }

    // Regular text
    return part
  })

  return (
    <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
      {elements}
    </div>
  )
}
