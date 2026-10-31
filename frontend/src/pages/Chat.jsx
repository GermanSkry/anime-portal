import { useState } from 'react'
import './Chat.css'
import { chatAPI } from '../services/api'

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: '👋 What anime are you looking for?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

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
        <div className="chat-item">Best action anime</div>
        <div className="chat-item">Like Toradora</div>
        <div className="chat-item">Dark fantasy recs</div>
      </div>
      <div className="chat-main">
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="bubble">{msg.text}</div>
            </div>
          ))}
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
