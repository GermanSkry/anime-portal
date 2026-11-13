import { useState, useEffect } from 'react'
import './Chat.css'
import { chatAPI } from '../services/api'
import MessageRenderer from '../components/MessageRenderer'

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: '👋 What anime are you looking for?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])

  const loadChatHistory = async () => {
    try {
      const data = await chatAPI.getHistory()
      if (data && Array.isArray(data)) {
        setHistory(data)
      }
    } catch (error) {
      console.error('Error loading history:', error)
      setHistory([])
    }
  }

  useEffect(() => {
    loadChatHistory()
  }, [])

  const loadHistoryChat = (item) => {
    // Load a previous conversation from history
    setMessages([
      { role: 'assistant', text: '👋 What anime are you looking for?' },
      { role: 'user', text: item.user_message },
      { role: 'assistant', text: item.assistant_response, animeReferences: item.anime_references || [] }
    ])
  }

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
    if (input.trim()) {
      const userMessage = input.trim()
      setMessages(prev => [...prev, { role: 'user', text: userMessage }])
      setInput('')
      setLoading(true)

      try {
        // Build history with summarization if > 5 messages
        const messageHistory = buildHistoryForAPI()

        const response = await chatAPI.send(userMessage, '', null, messageHistory)
        setMessages(prev => [...prev, {
          role: 'assistant',
          text: response.response || 'Sorry, I couldn\'t process that. Try asking about specific anime or genres!',
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
  }

  return (
    <div className="chat-container">
      <div className="sidebar">
        <div className="sidebar-title">Recent</div>
        {history.length > 0 ? (
          history.map((item, i) => (
            <div
              key={i}
              className="chat-item"
              onClick={() => loadHistoryChat(item)}
              title={item.user_message}
            >
              {item.user_message.substring(0, 30)}...
            </div>
          ))
        ) : (
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px', padding: '12px' }}>
            No chats yet
          </div>
        )}
      </div>
      <div className="chat-main">
        <div className="chat-messages">
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
        </div>
        <div className="chat-input-area">
          <input
            type="text"
            className="chat-input"
            placeholder="Ask..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          />
          <button className="send-btn" onClick={handleSend}>Send</button>
        </div>
      </div>
    </div>
  )
}
