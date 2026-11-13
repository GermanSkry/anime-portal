import { useState, useRef, useEffect } from 'react'
import '../styles/ChatModal.css'
import { chatAPI } from '../services/api'
import MessageRenderer from './MessageRenderer'

export default function ChatModal({ isOpen, onClose, animeContext = null }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: animeContext
      ? `📺 Discussing **${animeContext.title_english || animeContext.name}**...`
      : '👋 What anime are you looking for?'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const hasLoadedHistory = useRef(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const getCustomGreeting = () => {
    if (!animeContext) return '👋 What anime are you looking for?'

    const title = animeContext.title_english || animeContext.name
    const rating = animeContext.rating ? `★${animeContext.rating}/10` : null
    const genres = animeContext.genres?.slice(0, 2).join(', ') || null
    const year = animeContext.year

    const greetings = [
      `🎬 Let's dive into **${title}** (${year}, ${genres})! What would you like to know?`,
      `📺 Curious about **${title}**? I'm here to discuss this ${rating} anime with you!`,
      `✨ Welcome to **${title}**! Ask me anything about this ${genres} masterpiece.`,
      `🎭 Exploring **${title}** together! What interests you most about this series?`,
      `⚔️ **${title}** is calling! Let's talk about this ${rating} ${genres} anime.`
    ]

    return greetings[Math.floor(Math.random() * greetings.length)]
  }

  const loadChatHistory = async () => {
    // anime context loads that anime's history only
    const data = await chatAPI.getHistory(animeContext?.id ?? null, animeContext ? 20 : 10)
    if (Array.isArray(data) && data.length > 0) {
      // reverse to show oldest first
      const historyMessages = data.reverse().flatMap(item => [
        { role: 'user', text: item.user_message },
        { role: 'assistant', text: item.assistant_response, animeReferences: item.anime_references || [] }
      ])
      setMessages([
        { role: 'assistant', text: getCustomGreeting() },
        ...historyMessages
      ])
    }
  }

  // Load chat history on first open
  useEffect(() => {
    if (isOpen && !hasLoadedHistory.current) {
      hasLoadedHistory.current = true
      loadChatHistory()
    }
    // hasLoadedHistory guards the one-shot fetch, so loadChatHistory does not belong in the deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  const buildHistoryForAPI = () => {
    // Build message history, summarizing old messages if > 5
    if (messages.length <= 5) {
      // Keep all recent messages
      return messages.map(msg => ({
        role: msg.role,
        content: msg.text
      }))
    }

    // Summarize old messages to save tokens
    const recentMessages = messages.slice(-5)
    const oldMessages = messages.slice(0, -5)

    // Create a concise summary of old conversation
    const summary = oldMessages
      .map(msg => `${msg.role === 'user' ? 'User' : 'AI'}: ${msg.text.substring(0, 100)}...`)
      .join('\n')

    const systemSummary = {
      role: 'user',
      content: `[Earlier conversation summary]\n${summary}`
    }

    return [systemSummary, ...recentMessages.map(msg => ({
      role: msg.role,
      content: msg.text
    }))]
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

      // Build history with summarization if > 5 messages
      const messageHistory = buildHistoryForAPI()

      const response = await chatAPI.send(contextMessage, '', animeContext?.id, messageHistory)
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: response.response || 'Sorry, I couldn\'t process that. Try asking about this anime!',
        animeReferences: response.anime_references || []
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
              <div className="bubble">
                {msg.role === 'assistant' ? (
                  <MessageRenderer text={msg.text} animeReferences={msg.animeReferences} />
                ) : (
                  msg.text
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message assistant">
              <div className="bubble typing">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </div>
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
