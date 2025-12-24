import { useState, useRef, useEffect } from 'react'
import api from '../../utils/api'
import './AICoach.css'

function AICoach({ symbol, onClose }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Xin chào! Tôi là AI Coach, tôi có thể giúp bạn phân tích cổ phiếu, đưa ra lời khuyên đầu tư, và giải thích các khái niệm. Bạn muốn hỏi gì?'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    // Thêm user message
    const newMessages = [...messages, { role: 'user', content: userMessage }]
    setMessages(newMessages)

    try {
      const response = await api.post('/ai/chat', {
        question: userMessage,
        symbol: symbol || null
      })

      // Thêm AI response
      setMessages([
        ...newMessages,
        { role: 'assistant', content: response.data.response }
      ])
    } catch (error) {
      console.error('Error chatting with AI:', error)
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại sau.'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleAnalyzeStock = async () => {
    if (!symbol) {
      setMessages([
        ...messages,
        {
          role: 'assistant',
          content: 'Vui lòng chọn mã chứng khoán trước khi phân tích.'
        }
      ])
      return
    }

    setLoading(true)
    const analyzingMessage = { role: 'assistant', content: `Đang phân tích ${symbol}...` }
    setMessages([...messages, analyzingMessage])

    try {
      const response = await api.post('/ai/analyze', { symbol })
      setMessages([
        ...messages,
        { role: 'assistant', content: response.data.response }
      ])
    } catch (error) {
      console.error('Error analyzing stock:', error)
      setMessages([
        ...messages,
        {
          role: 'assistant',
          content: 'Xin lỗi, có lỗi xảy ra khi phân tích. Vui lòng thử lại sau.'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="ai-coach-container">
      <div className="ai-coach-header">
        <h3>AI Coach</h3>
        {symbol && (
          <button className="analyze-btn" onClick={handleAnalyzeStock} disabled={loading}>
            Phân tích {symbol}
          </button>
        )}
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="ai-coach-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <span className="typing-indicator">...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="ai-coach-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Nhập câu hỏi của bạn..."
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          Gửi
        </button>
      </div>
    </div>
  )
}

export default AICoach

