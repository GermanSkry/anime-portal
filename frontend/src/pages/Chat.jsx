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

  useEffect(() => {
    loadChatHistory()
  }, [])

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

  const handleSend = async () => {
    if (input.trim()) {
      const userMessage = input.trim()
      setMessages(prev => [...prev, { role: 'user', text: userMessage }])
      setInput('')
      setLoading(true)

      try {
        const response = await chatAPI.send(userMessage)
        setMessages(prev => [...prev, {
          role: 'assistant',
          text: response.response || 'Sorry, I couldn\'t process that. Try asking about specific anime or genres!'
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
              onClick={() => setMessages([
                { role: 'assistant', text: '👋 What anime are you looking for?' },
                { role: 'user', text: item.user_message },
                { role: 'assistant', text: item.assistant_response }
              ])}
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
                  <MessageRenderer text={msg.text} />
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
