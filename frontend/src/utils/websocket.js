/**
 * WebSocket utility để kết nối với backend WebSocket server
 */

class WebSocketClient {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.listeners = new Map()
  }

  connect(symbol, token = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const tokenParam = token ? `?token=${token}` : ''
      const url = `ws://localhost:8000/ws/ohlc/${symbol}${tokenParam}`

      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log(`WebSocket connected: ${symbol}`)
        this.reconnectAttempts = 0
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        reject(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.ws = null
        
        // Auto reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => {
            this.connect(symbol, token)
          }, this.reconnectDelay * this.reconnectAttempts)
        }
      }
    })
  }

  handleMessage(data) {
    const { type } = data

    if (type === 'connected') {
      console.log('WebSocket:', data.message)
    } else if (type === 'ohlc_update') {
      // Emit to all listeners
      this.listeners.forEach((callback) => {
        callback(data)
      })
    }
  }

  subscribe(callback) {
    const id = Date.now() + Math.random()
    this.listeners.set(id, callback)
    return () => this.listeners.delete(id)
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.listeners.clear()
  }

  ping() {
    this.send({ type: 'ping' })
  }
}

// Singleton instance
let wsClient = null

export const getWebSocketClient = () => {
  if (!wsClient) {
    wsClient = new WebSocketClient()
  }
  return wsClient
}

export default WebSocketClient

