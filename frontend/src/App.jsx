import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import './App.css'
import Chat from './pages/Chat'
import Browse from './pages/Browse'
import Explore from './pages/Explore'
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
            Anime Portal
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

        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="/title/:id" element={<Title />} />
        </Routes>
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
