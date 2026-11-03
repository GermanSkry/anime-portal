import { useState, useRef, useEffect } from 'react'
import '../styles/ChatModal.css'
import { chatAPI } from '../services/api'

export default function ChatModal({ isOpen, onClose, animeContext = null }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: animeContext
      ? `📺 Ask me about ${animeContext.title_english || animeContext.name}!`
      : '👋 What anime are you looking for?'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const messagesEndRef = useRef(null)
  const hasLoadedHistory = useRef(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load chat history on first open
  useEffect(() => {
    if (isOpen && !hasLoadedHistory.current) {
      loadChatHistory()
      hasLoadedHistory.current = true
    }
  }, [isOpen])

  const loadChatHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/chat/history?limit=10')
      if (response.ok) {
        const data = await response.json()
        setHistory(data)
      }
    } catch (error) {
      console.error('Error loading chat history:', error)
    }
  }

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage = input.trim()
    setMessages(prev => [...prev, { role: 'user', text: userMessage }])
    setInput('')
    setLoading(true)

    try {
      // If anime context provided, add it to the message
      let contextMessage = userMessage
      if (animeContext) {
        contextMessage = `[About ${animeContext.title_english || animeContext.name} - ID: ${animeContext.id}, Rating: ${animeContext.rating}/10, Genres: ${animeContext.genres?.join(', ') || 'N/A'}] ${userMessage}`
      }

      const response = await chatAPI.send(contextMessage, '', animeContext?.id)
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: response.response || 'Sorry, I couldn\'t process that. Try asking about this anime!'
      }])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Error connecting to chat service. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="chat-modal-overlay" onClick={onClose}>
      <div className="chat-modal" onClick={(e) => e.stopPropagation()}>
        <div className="chat-modal-header">
          <h3>{animeContext ? `💬 ${animeContext.title_english || animeContext.name}` : '💬 Chat'}</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="chat-modal-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="bubble">{msg.text}</div>
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <div className="bubble typing">⏳ Thinking...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-modal-input-area">
          <input
            type="text"
            className="chat-modal-input"
            placeholder={animeContext ? 'Ask about this anime...' : 'Ask...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button className="send-btn" onClick={handleSend} disabled={loading}>
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
