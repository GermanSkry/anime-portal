import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import './App.css'
import Chat from './pages/Chat'
import Browse from './pages/Browse'
// the whole route is split out: the graph and its renderer are only worth
// downloading for someone who opens Explore
const ExploreGraph = lazy(() => import('./pages/ExploreGraph'))
import Title from './pages/Title'

function AppLayout() {
  const location = useLocation()

  const tabs = [
    { id: 'chat', label: '💬 Chat', path: '/' },
    { id: 'browse', label: '🎬 Browse', path: '/browse' },
    { id: 'explore', label: '🔍 Explore', path: '/explore' }
  ]

  const currentTab = location.pathname === '/' ? 'chat' : location.pathname.split('/')[1] || 'chat'

  return (
    <div className="app">
      <div className="container">
        <Link to="/" style={{ textDecoration: 'none' }}>
          <h1 style={{
            marginBottom: '24px',
            background: 'linear-gradient(135deg, #d946ef, #06b6d4)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            cursor: 'pointer'
          }}>
            AnimeVibing
          </h1>
        </Link>

        <div className="tab-switcher">
          {tabs.map(tab => (
            <Link key={tab.id} to={tab.path} style={{ textDecoration: 'none' }}>
              <button
                className={`tab-btn ${currentTab === tab.id ? 'active' : ''}`}
              >
                {tab.label}
              </button>
            </Link>
          ))}
        </div>

        <Suspense fallback={<div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>Loading…</div>}>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/explore" element={<ExploreGraph />} />
          <Route path="/title/:id" element={<Title />} />
        </Routes>
        </Suspense>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
