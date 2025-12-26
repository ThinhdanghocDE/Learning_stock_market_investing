import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { createChart } from 'lightweight-charts'
import { getWebSocketClient } from '../../utils/websocket'
import { useAuthStore } from '../../stores/authStore'
import api from '../../utils/api'
import Modal from '../../components/Modal/Modal'
import AICoach from '../../components/AICoach/AICoach'
import './Trading.css'

function TradingPage() {
  const navigate = useNavigate()
  const { token } = useAuthStore()
  const [symbol, setSymbol] = useState('ACB')
  const [symbols, setSymbols] = useState([])
  const [companyInfo, setCompanyInfo] = useState(null) // Thông tin công ty
  const [popularSymbols, setPopularSymbols] = useState([]) // Danh sách mã có nhiều nến
  const [loading, setLoading] = useState(true)
  const [legendData, setLegendData] = useState({ open: '-', high: '-', low: '-', close: '-', volume: '-' })
  const [searchTerm, setSearchTerm] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isInputFocused, setIsInputFocused] = useState(false)
  const [startDate, setStartDate] = useState('')
  const [startTime, setStartTime] = useState('00:00')
  const [endDate, setEndDate] = useState('')
  const [endTime, setEndTime] = useState('23:59')

  // Challenge state
  const [challengeActive, setChallengeActive] = useState(false)
  const [challengeStartDate, setChallengeStartDate] = useState('')
  const [challengeStartTime, setChallengeStartTime] = useState('09:00')
  const [challengeDuration, setChallengeDuration] = useState('7') // 1, 7, 30 (ngày)
  const [challengeCapital, setChallengeCapital] = useState(10000000) // 10 triệu VNĐ
  const [challengeCurrentDate, setChallengeCurrentDate] = useState('')
  const [challengeEndDate, setChallengeEndDate] = useState('')
  const [chartViewStartDate, setChartViewStartDate] = useState('') // Ngày bắt đầu hiển thị chart
  const [challengeBalance, setChallengeBalance] = useState(10000000) // Số dư trong challenge (tách riêng)
  const [challengeTotalValue, setChallengeTotalValue] = useState(10000000) // Tổng giá trị trong challenge
  const [challengePositions, setChallengePositions] = useState([]) // Vị thế trong challenge (số lượng đã mua)
  const [pendingOrders, setPendingOrders] = useState([]) // Lệnh đang chờ (ATO/ATC)

  // Order form state
  const [orderSide, setOrderSide] = useState('BUY')
  const [orderType, setOrderType] = useState('LIMIT') // 'LIMIT', 'MTL', 'ATO', 'ATC'
  const [orderQuantity, setOrderQuantity] = useState('')
  const [orderPrice, setOrderPrice] = useState('')
  const [orderSubmitting, setOrderSubmitting] = useState(false)
  const [accountType, setAccountType] = useState('cash') // 'cash', 'margin'
  const [portfolio, setPortfolio] = useState(null)
  const [positions, setPositions] = useState([])

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [modalTitle, setModalTitle] = useState('')
  const [modalMessage, setModalMessage] = useState('')
  const [modalType, setModalType] = useState('info')

  // Rules modal state
  const [rulesModalOpen, setRulesModalOpen] = useState(false)

  // AI Coach state
  const [aiCoachOpen, setAiCoachOpen] = useState(false)


  // Helper function để hiển thị modal
  const showModal = (title, message, type = 'info') => {
    setModalTitle(title)
    setModalMessage(message)
    setModalType(type)
    setModalOpen(true)
  }

  // Hàm kiểm tra phiên giao dịch hiện tại
  const getCurrentSession = () => {
    const now = new Date()
    // Lấy giờ local (giả sử máy client đang ở múi giờ VN hoặc đã set đúng)
    const hours = now.getHours()
    const minutes = now.getMinutes()
    const time = hours * 100 + minutes // Ví dụ: 10:30 -> 1030

    if (time >= 900 && time <= 915) return 'ATO_SESSION'
    if (time > 915 && time < 1430) return 'CONTINUOUS_SESSION'
    if (time >= 1430 && time <= 1445) return 'ATC_SESSION'
    return 'OUT_OF_MARKET'
  }

  // Helper: Lấy giá mở cửa (open price) của candle đầu tiên trong ngày
  const getOpeningPrice = useCallback((symbol, date) => {
    if (!symbol || !date || historicalCandlesRef.current.length === 0) {
      return null
    }

    // Lọc candles của symbol và date
    const dateStr = typeof date === 'string' ? date : date.toISOString().split('T')[0]
    const candlesForDate = historicalCandlesRef.current.filter(candle => {
      const candleDate = typeof candle.time === 'string'
        ? candle.time.split('T')[0]
        : new Date(candle.time * 1000).toISOString().split('T')[0]
      return candleDate === dateStr
    })

    if (candlesForDate.length === 0) {
      return null
    }

    // Sắp xếp theo thời gian và lấy candle đầu tiên (sớm nhất)
    const sorted = candlesForDate.sort((a, b) => {
      const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : (a.time > 1e12 ? a.time : a.time * 1000)
      const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : (b.time > 1e12 ? b.time : b.time * 1000)
      return timeA - timeB
    })

    const firstCandle = sorted[0]
    return firstCandle ? parseFloat(firstCandle.open) : null
  }, [])

  // Helper: Lấy giá đóng cửa (close price) của candle cuối cùng trong ngày
  const getClosingPrice = useCallback((targetSymbol, date) => {
    console.log('getClosingPrice called with:', { targetSymbol, date, candlesCount: historicalCandlesRef.current.length })

    if (!targetSymbol || !date || historicalCandlesRef.current.length === 0) {
      console.warn('getClosingPrice: Missing params or no candles')
      return null
    }

    // Lọc candles của symbol và date
    const dateStr = typeof date === 'string' ? date : date.toISOString().split('T')[0]
    const candlesForDate = historicalCandlesRef.current.filter(candle => {
      const candleDate = typeof candle.time === 'string'
        ? candle.time.split('T')[0]
        : new Date(candle.time * 1000).toISOString().split('T')[0]
      // ⚠️ LƯU Ý: historicalCandlesRef chỉ chứa candles của symbol đang xem trong chart
      // Không có candle.symbol để filter, nên sẽ LUÔN lấy giá của symbol hiện tại
      return candleDate === dateStr
    })

    console.log('getClosingPrice: Found candles for date:', candlesForDate.length)

    if (candlesForDate.length === 0) {
      console.warn(`getClosingPrice: No candles found for ${targetSymbol} on ${dateStr}`)
      return null
    }

    // Sắp xếp theo thời gian và lấy candle cuối cùng (muộn nhất)
    const sorted = candlesForDate.sort((a, b) => {
      const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : (a.time > 1e12 ? a.time : a.time * 1000)
      const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : (b.time > 1e12 ? b.time : b.time * 1000)
      return timeA - timeB
    })

    const lastCandle = sorted[sorted.length - 1]
    const price = lastCandle ? parseFloat(lastCandle.close) : null
    console.log(`getClosingPrice: Result for ${targetSymbol}:`, price)
    return price
  }, [])

  // Hàm xử lý khi chọn bước nhảy
  const handleStepSelection = (selectedStep) => {
    if (!challengeActive || !selectedStep) return

    // Áp dụng bước nhảy được chọn
    expandChartOnOrder(selectedStep)
  }

  const searchInputRef = useRef(null)
  const suggestionsRef = useRef(null)
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const candlestickSeriesRef = useRef(null)
  const volumeSeriesRef = useRef(null)
  const vwapSeriesRef = useRef(null)
  const wsClientRef = useRef(null)
  const historicalCandlesRef = useRef([])
  const isExpandingChartRef = useRef(false)
  const challengeCurrentTimeRef = useRef('09:00') // Lưu thời gian hiện tại của challenge // Flag để tránh fetch trùng lặp khi expand chart
  const tokenRef = useRef(token)
  // Refs để tránh stale closure trong setInterval
  const pendingOrdersRef = useRef([])
  const processingATCOrdersRef = useRef(false)
  const processingATOOrdersRef = useRef(false)

  // Chart mode: LIVE (real-time) hoặc HISTORY (xem dữ liệu quá khứ)
  const [chartMode, setChartMode] = useState('LIVE') // 'LIVE' | 'HISTORY'

  // Update token ref khi token thay đổi (nhưng không trigger reconnect)
  useEffect(() => {
    tokenRef.current = token
  }, [token])

  // Fetch pending ATO/ATC orders từ DB
  useEffect(() => {
    const fetchPendingOrders = async () => {
      if (challengeActive) return // Không load trong challenge mode

      try {
        const response = await api.get('/portfolio/orders/pending-ato-atc')
        const orders = response.data || []

        // Chuyển đổi format từ DB sang format của pendingOrders state
        const formattedOrders = orders.map(order => ({
          id: order.id,
          symbol: order.symbol,
          side: order.side,
          orderType: order.order_type,
          quantity: order.quantity,
          status: order.status,
          targetTime: order.order_type === 'ATO' ? '09:15' : '14:45',
          targetDate: new Date(order.created_at).toISOString().split('T')[0], // YYYY-MM-DD
          createdAt: order.created_at
        }))

        setPendingOrders(formattedOrders)
        console.log('Loaded pending ATO/ATC orders from DB:', formattedOrders)
      } catch (error) {
        console.error('Error loading pending ATO/ATC orders:', error)
        // Không báo lỗi, chỉ log
      }
    }

    fetchPendingOrders()

    // Reload pending orders mỗi 30 giây để đảm bảo có dữ liệu mới nhất
    const interval = setInterval(fetchPendingOrders, 30000)
    return () => clearInterval(interval)
  }, [challengeActive])

  // Fetch portfolio và positions
  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        // Trước tiên, check và fill QUEUED orders và LIMIT orders nếu đang trong giờ giao dịch
        // (Ngoài giờ giao dịch không có giá real-time, nên không fill được)
        try {
          await api.post('/portfolio/check-queued-orders')
        } catch (checkError) {
          // Không báo lỗi nếu check fail (có thể ngoài giờ giao dịch)
          console.log('Check queued orders:', checkError.response?.data || checkError.message)
        }
        try {
          await api.post('/portfolio/check-limit-orders')
        } catch (checkError) {
          // Không báo lỗi nếu check fail
          console.log('Check limit orders:', checkError.response?.data || checkError.message)
        }

        // Sau đó fetch dữ liệu mới nhất
        // Endpoint /api/portfolio trả về PortfolioResponse trực tiếp (không có wrapper)
        // Endpoint /api/portfolio/summary trả về {portfolio, positions, ...}
        const response = await api.get('/portfolio/summary')
        console.log('Portfolio summary response:', response.data)
        if (response.data && response.data.portfolio) {
          setPortfolio(response.data.portfolio)
          setPositions(response.data.positions || [])
        } else {
          // Fallback: dùng endpoint /portfolio (trả về trực tiếp PortfolioResponse)
          const portfolioResponse = await api.get('/portfolio')
          console.log('Portfolio response (fallback):', portfolioResponse.data)
          setPortfolio(portfolioResponse.data)
          // Fetch positions riêng
          try {
            const positionsResponse = await api.get('/portfolio/positions')
            setPositions(positionsResponse.data || [])
          } catch (posError) {
            console.error('Error fetching positions:', posError)
            setPositions([])
          }
        }
      } catch (error) {
        console.error('Error fetching portfolio:', error)
        // Fallback: thử endpoint /portfolio nếu /summary fail
        try {
          const portfolioResponse = await api.get('/portfolio')
          console.log('Portfolio response (error fallback):', portfolioResponse.data)
          setPortfolio(portfolioResponse.data)
          // Fetch positions riêng
          try {
            const positionsResponse = await api.get('/portfolio/positions')
            setPositions(positionsResponse.data || [])
          } catch (posError) {
            setPositions([])
          }
        } catch (fallbackError) {
          console.error('Error fetching portfolio (fallback):', fallbackError)
        }
      }
    }

    if (token) {
      fetchPortfolio()
      // Refresh portfolio mỗi 5 giây để cập nhật giá và fill QUEUED orders
      const interval = setInterval(fetchPortfolio, 5000)
      return () => clearInterval(interval)
    }
  }, [token])

  // Hàm xử lý lệnh ATO khi đến 09:15
  const processATOOrders = useCallback(async () => {
    // Dùng ref để tránh stale closure
    const currentPendingOrders = pendingOrdersRef.current

    if (challengeActive || currentPendingOrders.length === 0) return

    // Tránh xử lý đồng thời
    if (processingATOOrdersRef.current) return
    processingATOOrdersRef.current = true

    const now = new Date()
    const hours = now.getHours()
    const minutes = now.getMinutes()
    const time = hours * 100 + minutes

    // Chỉ xử lý sau 09:15
    if (time < 915) {
      processingATOOrdersRef.current = false
      return
    }

    const today = now.toISOString().split('T')[0]
    const atoOrders = currentPendingOrders.filter(
      order => order.orderType === 'ATO'
        && order.status === 'PENDING'
        && order.targetDate === today
    )

    if (atoOrders.length === 0) {
      processingATOOrdersRef.current = false
      return
    }

    console.log('Processing ATO orders:', atoOrders)

    for (const order of atoOrders) {
      try {
        // Lấy giá mở cửa từ API thay vì local data (vì local chỉ có symbol đang view)
        let openingPrice = null
        try {
          const priceResponse = await api.get(`/ohlc/${order.symbol}/price`)
          // Dùng giá mở cửa của phiên hiện tại
          openingPrice = priceResponse.data?.open || priceResponse.data?.price
          console.log(`Got opening price for ${order.symbol}: ${openingPrice}`)
        } catch (priceError) {
          console.warn(`Cannot get price for ${order.symbol}:`, priceError)
          // Fallback: thử dùng local data nếu đang xem đúng symbol
          openingPrice = getOpeningPrice(order.symbol, order.targetDate)
        }

        if (!openingPrice || openingPrice <= 0) {
          console.warn(`Cannot get opening price for ${order.symbol} on ${order.targetDate}`)
          continue
        }

        // Kiểm tra số dư/số lượng trước khi khớp
        if (order.side === 'BUY') {
          const availableBalance = portfolio ? parseFloat(portfolio.cash_balance || 0) : 0
          const requiredAmount = openingPrice * order.quantity * 1000 // Giá là nghìn VNĐ

          if (requiredAmount > availableBalance) {
            console.warn(`Insufficient balance for ATO order ${order.id}`)
            continue
          }
        } else if (order.side === 'SELL') {
          const existing = positions.find(p => p.symbol === order.symbol)
          if (!existing || existing.quantity < order.quantity) {
            console.warn(`Insufficient quantity for ATO order ${order.id}`)
            continue
          }
        }

        // Gọi API để fill order ATO ở giá mở cửa
        const response = await api.post(`/portfolio/orders/${order.id}/fill?fill_price=${openingPrice}`)
        console.log('ATO order fill API response:', response.data)

        // Kiểm tra response kỹ lưỡng
        if (!response.data || response.data.status !== 'FILLED') {
          console.warn(`Fill API did not return FILLED status for order ${order.id}. Response:`, response.data)
          // Không remove khỏi pending, để retry sau
          continue
        }

        // Cập nhật status của lệnh (dùng functional update để tránh stale state)
        setPendingOrders(prev => {
          const updated = prev.filter(p => p.id !== order.id)
          console.log(`Removed order ${order.id} from pending. Remaining:`, updated.length)
          return updated
        })

        // Refresh portfolio
        const portfolioResponse = await api.get('/portfolio/summary')
        if (portfolioResponse.data) {
          setPortfolio(portfolioResponse.data.portfolio)
          setPositions(portfolioResponse.data.positions || [])
        }

        showModal('Lệnh ATO đã khớp', `Lệnh ${order.symbol} ${order.side} ${order.quantity} cổ đã khớp ở giá mở cửa ${(openingPrice * 1000).toLocaleString('vi-VN')} VNĐ`, 'success')
      } catch (error) {
        console.error(`Error processing ATO order ${order.id}:`, error)
        // Log chi tiết để debug
        if (error.response) {
          console.error('API Error Response:', error.response.data, 'Status:', error.response.status)
        }
      }
    }

    // Release lock
    processingATOOrdersRef.current = false
  }, [challengeActive, portfolio, positions, getOpeningPrice])

  // Sync ref với state để tránh stale closure
  useEffect(() => {
    pendingOrdersRef.current = pendingOrders
  }, [pendingOrders])

  // Hàm xử lý lệnh ATC khi đến 14:45
  const processATCOrders = useCallback(async () => {
    // Lock để tránh xử lý đồng thời
    if (processingATCOrdersRef.current) {
      console.log('processATCOrders: Already processing, skipping...')
      return
    }

    if (challengeActive) {
      console.log('processATCOrders: Skipping - challengeActive:', challengeActive)
      return
    }

    // Dùng ref để tránh stale closure
    const currentPendingOrders = pendingOrdersRef.current
    if (currentPendingOrders.length === 0) {
      console.log('processATCOrders: No pending orders')
      return
    }

    const now = new Date()
    const hours = now.getHours()
    const minutes = now.getMinutes()
    const time = hours * 100 + minutes

    // Chỉ xử lý sau 14:45
    if (time < 1445) {
      console.log('processATCOrders: Time check failed. Current time:', `${hours}:${minutes.toString().padStart(2, '0')}`, 'Required: >= 14:45')
      return
    }

    // Fix timezone: dùng giờ VN thay vì UTC
    const todayVN = new Date(now.getTime() + (7 * 60 * 60 * 1000)).toISOString().split('T')[0] // UTC+7
    console.log('processATCOrders: Looking for ATC orders. Today (VN):', todayVN, 'All pending orders:', currentPendingOrders)

    // Xử lý tất cả ATC orders pending (không chỉ của hôm nay, vì có thể có lệnh của ngày trước chưa được xử lý)
    const atcOrders = currentPendingOrders.filter(
      order => order.orderType === 'ATC'
        && order.status === 'PENDING'
        // Xử lý cả lệnh của hôm nay và các ngày trước (nếu chưa được xử lý)
        && (order.targetDate === todayVN || new Date(order.targetDate) <= new Date(todayVN))
    )

    if (atcOrders.length === 0) {
      console.log('processATCOrders: No ATC orders to process. Today:', todayVN, 'Pending orders count:', currentPendingOrders.length)
      return
    }

    // Set lock
    processingATCOrdersRef.current = true
    console.log('processATCOrders: Processing ATC orders:', atcOrders)

    for (const order of atcOrders) {
      try {
        console.log(`Processing ATC order for ${order.symbol}:`, order)

        // ⚠️ BUG FIX: historicalCandlesRef chỉ chứa candles của symbol đang xem
        // Không thể dùng để lấy giá của symbol khác
        // → LUÔN fetch từ API để đảm bảo đúng symbol

        let closingPrice = null

        // LUÔN fetch từ API để đảm bảo lấy đúng symbol
        console.log(`Fetching closing price from API for ${order.symbol} on ${order.targetDate}`)
        try {
          // Fetch candle cuối cùng của ngày từ API
          const endDateTime = `${order.targetDate}T15:00:00+07:00`
          const priceResponse = await api.get(
            `/ohlc/historical?symbol=${order.symbol}&interval=1m&limit=1000&end_time=${encodeURIComponent(endDateTime)}`
          )

          console.log(`API response for ${order.symbol}:`, priceResponse.data?.data?.length, 'candles')

          if (priceResponse.data?.data && priceResponse.data.data.length > 0) {
            // Lọc candles của ngày hôm đó
            const candlesForDate = priceResponse.data.data.filter(candle => {
              const candleDate = typeof candle.time === 'string'
                ? candle.time.split('T')[0]
                : new Date(candle.time * 1000).toISOString().split('T')[0]
              return candleDate === order.targetDate
            })

            console.log(`Filtered candles for ${order.symbol} on ${order.targetDate}:`, candlesForDate.length)

            if (candlesForDate.length > 0) {
              // Sắp xếp theo thời gian và lấy candle cuối cùng
              const sorted = candlesForDate.sort((a, b) => {
                const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : (a.time > 1e12 ? a.time : a.time * 1000)
                const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : (b.time > 1e12 ? b.time : b.time * 1000)
                return timeA - timeB
              })
              const lastCandle = sorted[sorted.length - 1]
              closingPrice = lastCandle ? parseFloat(lastCandle.close) : null
              console.log(`Closing price for ${order.symbol}:`, closingPrice, 'from candle:', lastCandle)
            }
          }
        } catch (apiError) {
          console.error(`Error fetching closing price from API for ${order.symbol}:`, apiError)
        }

        if (!closingPrice || closingPrice <= 0) {
          console.warn(`Cannot get closing price for ${order.symbol} on ${order.targetDate}. Order will be retried later.`)
          continue
        }

        console.log(`✅ Will fill ATC order: ${order.symbol} ${order.side} ${order.quantity} @ ${closingPrice}`)

        // Kiểm tra số dư/số lượng trước khi khớp
        if (order.side === 'BUY') {
          const availableBalance = portfolio ? parseFloat(portfolio.cash_balance || 0) : 0
          const requiredAmount = closingPrice * order.quantity * 1000 // Giá là nghìn VNĐ

          if (requiredAmount > availableBalance) {
            console.warn(`Insufficient balance for ATC order ${order.id}`)
            continue
          }
        } else if (order.side === 'SELL') {
          const existing = positions.find(p => p.symbol === order.symbol)
          if (!existing || existing.quantity < order.quantity) {
            console.warn(`Insufficient quantity for ATC order ${order.id}`)
            continue
          }
        }

        // Gọi API để fill order ATC ở giá đóng cửa
        const response = await api.post(`/portfolio/orders/${order.id}/fill?fill_price=${closingPrice}`)
        console.log('ATC order fill API response:', response.data)

        // Kiểm tra response kỹ lưỡng
        if (!response.data || response.data.status !== 'FILLED') {
          console.warn(`Fill API did not return FILLED status for order ${order.id}. Response:`, response.data)
          // Không remove khỏi pending, để retry sau
          continue
        }

        // Cập nhật status của lệnh (dùng functional update để tránh stale state)
        setPendingOrders(prev => {
          const updated = prev.filter(p => p.id !== order.id)
          console.log(`Removed order ${order.id} from pending. Remaining:`, updated.length)
          return updated
        })

        // Refresh portfolio
        const portfolioResponse = await api.get('/portfolio/summary')
        if (portfolioResponse.data) {
          setPortfolio(portfolioResponse.data.portfolio)
          setPositions(portfolioResponse.data.positions || [])
        }

        showModal('Lệnh ATC đã khớp', `Lệnh ${order.symbol} ${order.side} ${order.quantity} cổ đã khớp ở giá đóng cửa ${(closingPrice * 1000).toLocaleString('vi-VN')} VNĐ`, 'success')
      } catch (error) {
        console.error(`Error processing ATC order ${order.id}:`, error)
        // Log chi tiết để debug
        if (error.response) {
          console.error('API Error Response:', error.response.data, 'Status:', error.response.status)
        }
      }
    }

    // Release lock
    processingATCOrdersRef.current = false
  }, [challengeActive, portfolio, positions, getClosingPrice])

  // useEffect để trigger xử lý ATO/ATC theo thời gian thực
  useEffect(() => {
    if (challengeActive) return // Không xử lý trong challenge mode

    const checkAndProcess = () => {
      const now = new Date()
      const hours = now.getHours()
      const minutes = now.getMinutes()
      const time = hours * 100 + minutes

      // Xử lý ATO sau 09:15
      if (time >= 915) {
        console.log('Triggering processATOOrders at', `${hours}:${minutes.toString().padStart(2, '0')}`)
        processATOOrders()
      }

      // Xử lý ATC sau 14:45
      if (time >= 1445) {
        console.log('Triggering processATCOrders at', `${hours}:${minutes.toString().padStart(2, '0')}`)
        processATCOrders()
      }
    }

    const interval = setInterval(checkAndProcess, 30000) // Check mỗi 30 giây (thay vì 1 phút để xử lý nhanh hơn)

    // Xử lý ngay lần đầu nếu đã qua thời gian
    checkAndProcess()

    return () => clearInterval(interval)
  }, [challengeActive, processATOOrders, processATCOrders])

  useEffect(() => {
    // Fetch symbols
    const fetchSymbols = async () => {
      try {
        // Fetch tất cả symbols (không giới hạn)
        const response = await api.get('/symbols')
        console.log('Symbols response:', response.data)

        // Handle different response formats
        let symbolsList = []
        if (response.data.symbols && Array.isArray(response.data.symbols)) {
          symbolsList = response.data.symbols.map(s => s.symbol || s)
        } else if (Array.isArray(response.data)) {
          symbolsList = response.data.map(s => s.symbol || s)
        }

        // Fallback to default symbol if empty
        if (symbolsList.length === 0) {
          symbolsList = ['ACB', 'VCB', 'VIC', 'VNM', 'FPT']
        }

        setSymbols(symbolsList)
        setLoading(false)
      } catch (error) {
        console.error('Error fetching symbols:', error)
        // Fallback to default symbols on error
        setSymbols(['ACB', 'VCB', 'VIC', 'VNM', 'FPT'])
        setLoading(false)
      }
    }

    fetchSymbols()
  }, [])

  // Fetch thông tin công ty khi symbol thay đổi
  useEffect(() => {
    const fetchCompanyInfo = async () => {
      if (!symbol) {
        setCompanyInfo(null)
        return
      }

      try {
        const response = await api.get(`/symbols/${symbol}`)
        if (response.data && response.data.data) {
          setCompanyInfo(response.data.data)
        } else {
          setCompanyInfo(null)
        }
      } catch (error) {
        console.error('Error fetching company info:', error)
        setCompanyInfo(null)
      }
    }

    fetchCompanyInfo()
  }, [symbol])

  // Fetch popular symbols (có nhiều nến)
  useEffect(() => {
    // Sử dụng danh sách mã từ download_vnstock_intraday.py
    const popularSymbolsList = [
      'BSR', 'CEO', 'HPG', 'MBB', 'VPB', 'SHB', 'FPT', 'MSN', 'TCB', 'STB',
      'CTG', 'VNM', 'ACB', 'DGC', 'DBC', 'VCB', 'HDB', 'DCM', 'BID', 'CII',
      'EIB', 'BAF', 'GAS', 'LPB', 'CTD', 'CTS', 'AAA', 'ANV', 'CSV', 'DDV'
    ]
    // Sắp xếp theo bảng chữ cái
    const sortedList = popularSymbolsList.sort((a, b) => a.localeCompare(b))
    setPopularSymbols(sortedList)
  }, [])


  useEffect(() => {
    // Cleanup chart cũ trước khi tạo mới
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }
    candlestickSeriesRef.current = null
    volumeSeriesRef.current = null
    vwapSeriesRef.current = null

    if (!chartContainerRef.current) return

    // Ensure container has dimensions
    const container = chartContainerRef.current
    if (container.clientWidth === 0 || container.clientHeight === 0) {
      console.warn('Chart container has no dimensions, retrying...')
      const timeout = setTimeout(() => {
        if (chartContainerRef.current && chartContainerRef.current.clientWidth > 0) {
          // Retry initialization
          const retryContainer = chartContainerRef.current
          initializeChart(retryContainer)
        }
      }, 100)
      return () => clearTimeout(timeout)
    }

    initializeChart(container)
  }, [symbol, challengeActive])

  // Tách hàm khởi tạo chart ra riêng
  const initializeChart = useCallback((container) => {
    if (!container) return

    // Initialize chart với dark theme
    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight || 500,
      layout: {
        background: { color: '#1e1e1e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#333' },
        horzLines: { color: '#333' },
      },
      rightPriceScale: {
        scaleMargins: { top: 0.1, bottom: 0.25 }, // Chừa 25% phía dưới cho Volume
        borderColor: '#555',
      },
      timeScale: {
        borderColor: '#555',
        timeVisible: true,
        secondsVisible: false,
      },
      localization: {
        // Format time hiển thị theo giờ Việt Nam (có cả ngày và giờ)
        // LƯU Ý: timestamp đã được cộng 7 giờ (UTC+7 offset), nên cần parse như UTC
        // và KHÔNG convert sang timezone nữa (vì đã adjust rồi)
        timeFormatter: (timestamp) => {
          // Timestamp đã là UTC+7 (đã cộng 7h), parse như UTC và format
          const date = new Date(timestamp * 1000)
          // Format như UTC (không convert sang timezone vì đã adjust rồi)
          const year = date.getUTCFullYear()
          const month = String(date.getUTCMonth() + 1).padStart(2, '0')
          const day = String(date.getUTCDate()).padStart(2, '0')
          const hour = String(date.getUTCHours()).padStart(2, '0')
          const minute = String(date.getUTCMinutes()).padStart(2, '0')
          return `${day}/${month}/${year}, ${hour}:${minute}`
        },
      },
    })

    // 1. Candlestick Series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })

    // 2. Volume Histogram Series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: '', // Overlay mode
    })

    // Cấu hình Volume nằm ở đáy biểu đồ
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    // 3. VWAP Line Series
    const vwapSeries = chart.addLineSeries({
      color: '#2196F3',
      lineWidth: 2,
      title: 'VWAP',
    })

    // 4. Xử lý Crosshair để cập nhật Legend
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || param.point.x < 0 || param.point.y < 0) {
        // Hiển thị nến cuối nếu không hover
        const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
        if (lastCandle) {
          setLegendData({
            open: lastCandle.open?.toFixed(2) || '-',
            high: lastCandle.high?.toFixed(2) || '-',
            low: lastCandle.low?.toFixed(2) || '-',
            close: lastCandle.close?.toFixed(2) || '-',
            volume: (lastCandle.volume || 0).toLocaleString(),
          })
        }
        return
      }

      const candle = param.seriesData.get(candlestickSeries)
      const volume = param.seriesData.get(volumeSeries)

      if (candle) {
        setLegendData({
          open: candle.open?.toFixed(2) || '-',
          high: candle.high?.toFixed(2) || '-',
          low: candle.low?.toFixed(2) || '-',
          close: candle.close?.toFixed(2) || '-',
          volume: (volume?.value || 0).toLocaleString(),
        })
      }
    })

    chartRef.current = chart
    candlestickSeriesRef.current = candlestickSeries
    volumeSeriesRef.current = volumeSeries
    vwapSeriesRef.current = vwapSeries

    // Handle resize
    const handleResize = () => {
      if (container && chartRef.current) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
          height: container.clientHeight || 500,
        })
      }
    }

    window.addEventListener('resize', handleResize)
  }, [])

  // Cleanup effect riêng cho resize handler
  useEffect(() => {
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight || 500,
        })
      }
    }

    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  // Update chart với tất cả series
  // Hàm cập nhật challenge total value dựa trên giá hiện tại
  const updateChallengeTotalValue = useCallback(() => {
    if (!challengeActive || challengePositions.length === 0) {
      return
    }

    // Lấy giá hiện tại từ candle cuối cùng
    const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
    if (lastCandle && lastCandle.close) {
      const currentPrice = parseFloat(lastCandle.close)

      // Tính tổng giá trị positions (mỗi position có thể là symbol khác nhau)
      // Lưu ý: currentPrice là nghìn VNĐ, challengeBalance là VNĐ, cần nhân 1000 khi tính positionsValue
      let positionsValue = 0
      challengePositions.forEach(pos => {
        // Nếu position là symbol hiện tại, dùng giá hiện tại
        // Nếu không, tạm thời dùng giá trung bình đã mua (có thể cải thiện sau bằng cách fetch giá cho từng symbol)
        const price = pos.symbol === symbol ? currentPrice : (pos.avg_price || currentPrice)
        positionsValue += pos.quantity * price * 1000 // Nhân 1000 để đổi từ nghìn VNĐ sang VNĐ
      })

      // Total value = cash balance + positions value
      const newTotalValue = challengeBalance + positionsValue
      setChallengeTotalValue(newTotalValue)
    }
  }, [challengeActive, challengePositions, challengeBalance, symbol])

  const updateChart = useCallback(() => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current || !vwapSeriesRef.current) return
    if (historicalCandlesRef.current.length === 0) return

    const sorted = [...historicalCandlesRef.current].sort((a, b) => {
      const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : (a.time * 1000)
      const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : (b.time * 1000)
      return timeA - timeB
    })

    // Helper function để convert time sang timestamp (UTC)
    // Data từ ClickHouse đã là UTC+7 (naive datetime), cần convert về UTC timestamp
    // TradingView Charts cần UTC timestamp (seconds), nhưng sẽ hiển thị theo timezone đã set
    const normalizeTime = (time) => {
      if (typeof time === 'string') {
        // Parse string time từ ClickHouse
        // Format thực tế: "2025-12-19T14:59:00" (ISO format, naive, UTC+7)

        // Check xem có timezone indicator ở cuối string không
        const hasTimezone = time.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(time)

        if (!hasTimezone) {
          // Data từ ClickHouse: "2025-12-19T14:59:00" (UTC+7, naive)
          // 
          // QUAN TRỌNG: Lightweight Charts hiểu mọi thứ là UTC và hiển thị theo UTC
          // 
          // Cách 1: Cộng offset trực tiếp vào timestamp
          // - Parse "2025-12-19T14:59:00" như UTC+7 → timestamp của 07:59 UTC
          // - Cộng thêm 7 giờ (7 * 3600 giây) → timestamp của 14:59 UTC
          // - Chart hiển thị: 14:59 UTC = 14:59 giờ VN (đúng)
          const dtVN = new Date(time + '+07:00') // Parse như UTC+7
          const utcTimestamp = Math.floor(dtVN.getTime() / 1000) // UTC timestamp (seconds)
          const vnHanoiOffset = 7 * 60 * 60 // 7 giờ tính bằng giây
          const timestamp = utcTimestamp + vnHanoiOffset // Cộng thêm 7 giờ

          return timestamp
        } else {
          // Đã có timezone info (Z hoặc +HH:MM/-HH:MM), parse trực tiếp
          return Math.floor(new Date(time).getTime() / 1000)
        }
      } else if (typeof time === 'number') {
        // Nếu đã là timestamp (seconds), return trực tiếp
        // Nếu là milliseconds, convert sang seconds
        return time > 1e12 ? Math.floor(time / 1000) : time
      }
      return 0
    }

    const candleData = sorted.map((c, index) => {
      const timestamp = normalizeTime(c.time)

      // Debug: Log first candle để kiểm tra conversion
      if (index === 0) {
        const originalTime = c.time
        const utcDate = new Date(timestamp * 1000).toISOString()
        const vnDate = new Date(timestamp * 1000).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })
        console.log('🔍 Time conversion check:', {
          original: originalTime,
          utcTimestamp: timestamp,
          utcDate: utcDate,
          vnDate: vnDate,
          expectedVN: originalTime // Nên match với original nếu conversion đúng
        })
      }

      return {
        time: timestamp,
        open: parseFloat(c.open) || 0,
        high: parseFloat(c.high) || 0,
        low: parseFloat(c.low) || 0,
        close: parseFloat(c.close) || 0,
      }
    }).filter(c => c.time > 0)

    const volData = sorted.map(c => {
      const timestamp = normalizeTime(c.time)
      return {
        time: timestamp,
        value: parseFloat(c.volume || 0),
        color: (parseFloat(c.close) >= parseFloat(c.open))
          ? 'rgba(38, 166, 154, 0.5)'
          : 'rgba(239, 83, 80, 0.5)',
      }
    }).filter(c => c.time > 0)

    const vwapData = sorted.map(c => {
      const timestamp = normalizeTime(c.time)
      return {
        time: timestamp,
        value: parseFloat(c.vwap || 0),
      }
    }).filter(c => c.time > 0 && c.value > 0)

    candlestickSeriesRef.current.setData(candleData)
    volumeSeriesRef.current.setData(volData)
    vwapSeriesRef.current.setData(vwapData)

    // Fit content để hiển thị toàn bộ data
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }

    // Cập nhật challenge total value sau khi update chart
    if (challengeActive && challengePositions.length > 0) {
      const lastCandle = sorted[sorted.length - 1]
      if (lastCandle && lastCandle.close) {
        const currentPrice = parseFloat(lastCandle.close)
        // Lưu ý: currentPrice là nghìn VNĐ, challengeBalance là VNĐ, cần nhân 1000
        let positionsValue = 0
        challengePositions.forEach(pos => {
          const price = pos.symbol === symbol ? currentPrice : (pos.avg_price || currentPrice)
          positionsValue += pos.quantity * price * 1000 // Nhân 1000 để đổi từ nghìn VNĐ sang VNĐ
        })
        const newTotalValue = challengeBalance + positionsValue
        setChallengeTotalValue(newTotalValue)
      }
    }

    if (chartRef.current) {
      // Set custom time formatter để hiển thị đúng giờ Việt Nam (UTC+7)
      chartRef.current.timeScale().applyOptions({
        timeVisible: true,
        // Custom formatter: convert UTC timestamp về giờ VN và format
        // Chart nhận UTC timestamp, nhưng hiển thị theo browser timezone
        // Nếu browser timezone không phải UTC+7, cần adjust
      })
      chartRef.current.timeScale().fitContent()
    }

    // Update legend với nến cuối
    if (sorted.length > 0) {
      const lastCandle = sorted[sorted.length - 1]
      setLegendData({
        open: parseFloat(lastCandle.open).toFixed(2),
        high: parseFloat(lastCandle.high).toFixed(2),
        low: parseFloat(lastCandle.low).toFixed(2),
        close: parseFloat(lastCandle.close).toFixed(2),
        volume: (lastCandle.volume || 0).toLocaleString(),
      })
    }
  }, [])

  // Update hoặc append candle mới
  const updateOrAppendCandle = useCallback((newCandle) => {
    // 1. Chặn cập nhật nếu đang trong Challenge hoặc History
    if (startDate || endDate || challengeActive) return
    if (!candlestickSeriesRef.current) return

    // 2. Normalize Time
    const normalizeTime = (time) => {
      if (typeof time === 'string') {
        const hasTimezone = time.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(time)
        if (!hasTimezone) {
          const dtVN = new Date(time + '+07:00')
          return (dtVN.getTime() + 7 * 3600000) / 1000
        }
        return Math.floor(new Date(time).getTime() / 1000)
      }
      return time > 1e12 ? Math.floor(time / 1000) : time
    }

    const timestamp = normalizeTime(newCandle.time)
    const lastBar = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]

    // 3. BỘ LỌC RÁC (Chặn giá ảo làm nén chart)
    if (lastBar) {
      const priceChange = Math.abs(newCandle.close - lastBar.close) / lastBar.close
      if (priceChange > 0.10) { // Nếu lệch > 10% trong 1 phút -> Bỏ qua
        console.warn("Chặn nến ảo:", newCandle.close, "Giá cũ:", lastBar.close, "Lệch:", (priceChange * 100).toFixed(2) + "%")
        return
      }
    }

    // 4. CẬP NHẬT TRỰC TIẾP (Không dùng setData)
    const candleData = {
      time: timestamp,
      open: parseFloat(newCandle.open),
      high: parseFloat(newCandle.high),
      low: parseFloat(newCandle.low),
      close: parseFloat(newCandle.close),
    }

    candlestickSeriesRef.current.update(candleData)

    if (volumeSeriesRef.current) {
      volumeSeriesRef.current.update({
        time: timestamp,
        value: parseFloat(newCandle.volume || 0),
        color: candleData.close >= candleData.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
      })
    }

    if (vwapSeriesRef.current && newCandle.vwap) {
      vwapSeriesRef.current.update({ time: timestamp, value: parseFloat(newCandle.vwap) })
    }

    // Cập nhật Ref lịch sử để khi hover chuột (Legend) vẫn có dữ liệu mới nhất
    const index = historicalCandlesRef.current.findIndex(c => {
      const cTime = normalizeTime(c.time)
      return Math.abs(cTime - timestamp) < 60 // 1 phút
    })

    if (index !== -1) {
      historicalCandlesRef.current[index] = newCandle
    } else {
      historicalCandlesRef.current.push(newCandle)
      if (historicalCandlesRef.current.length > 1000) historicalCandlesRef.current.shift()
    }

    // Cập nhật legend cho mượt
    setLegendData({
      open: candleData.open.toFixed(2),
      high: candleData.high.toFixed(2),
      low: candleData.low.toFixed(2),
      close: candleData.close.toFixed(2),
      volume: (newCandle.volume || 0).toLocaleString(),
    })
  }, [startDate, endDate, challengeActive])

  // Hàm fetch data (tách ra để có thể gọi từ nút tìm kiếm)
  const fetchChartData = useCallback(async () => {
    if (!symbol || !candlestickSeriesRef.current) {
      console.log('Waiting for symbol or chart series...', { symbol, hasSeries: !!candlestickSeriesRef.current })
      return
    }

    setLoading(true)
    // 1. XÓA DỮ LIỆU TRÊN BIỂU ĐỒ 
    candlestickSeriesRef.current.setData([]);
    volumeSeriesRef.current.setData([]);
    vwapSeriesRef.current.setData([]);

    // 2. Xóa dữ liệu trong Ref
    historicalCandlesRef.current = [];

    try {
      console.log('Fetching historical data for:', symbol, { startDate, endDate, challengeActive })

      // Nếu đang trong challenge, sử dụng challenge dates
      let actualStartDate = startDate
      let actualEndDate = endDate
      let actualStartTime = startTime
      let actualEndTime = endTime

      if (challengeActive && chartViewStartDate) {
        actualStartDate = chartViewStartDate
        actualStartTime = '00:00' // Chart view luôn bắt đầu từ 00:00

        // End date là challengeCurrentDate hoặc challengeStartDate
        actualEndDate = challengeCurrentDate || challengeStartDate

        // End time: nếu đang ở ngày bắt đầu, dùng challengeStartTime, nếu không thì dùng 23:59
        if (actualEndDate === challengeStartDate) {
          actualEndTime = challengeStartTime
        } else {
          actualEndTime = '23:59'
        }
      }

      // Build query params
      // Xác định mode: HISTORY nếu có date filter, LIVE nếu không có
      const isHistoryMode = !!(actualStartDate || actualEndDate)

      // LIVE mode: limit=200 (chỉ lấy 200 candles gần nhất)
      // HISTORY mode: limit=10000 (lấy đủ dữ liệu trong khoảng thời gian)
      const limit = isHistoryMode ? 10000 : 1000
      let url = `/ohlc/historical?symbol=${symbol}&interval=1m&limit=${limit}`

      if (actualStartDate) {
        // Format: YYYY-MM-DDTHH:MM:SS (UTC+7 timezone)
        const startDateTime = `${actualStartDate}T${actualStartTime}:00+07:00`
        url += `&start_time=${encodeURIComponent(startDateTime)}`
      }
      if (actualEndDate) {
        // Format: YYYY-MM-DDTHH:MM:SS (UTC+7 timezone)
        // Nếu endTime có giây, giữ nguyên, nếu không thì thêm :00
        const endTimeParts = actualEndTime.split(':')
        const endTimeFormatted = endTimeParts.length === 2 ? `${actualEndTime}:00` : actualEndTime
        const endDateTime = `${actualEndDate}T${endTimeFormatted}+07:00`
        url += `&end_time=${encodeURIComponent(endDateTime)}`
      }

      // Set chart mode dựa trên date filter
      setChartMode(isHistoryMode ? 'HISTORY' : 'LIVE')

      console.log('Fetch URL:', url)
      console.log('Date range:', { actualStartDate, actualEndDate, startTime, endTime })

      const response = await api.get(url)
      console.log('Historical data response:', response.data)

      if (!response.data.data || response.data.data.length === 0) {
        console.warn('No historical data received')
        setLoading(false)
        return
      }

      // Store historical candles
      historicalCandlesRef.current = response.data.data.map(candle => ({
        time: candle.time,
        open: parseFloat(candle.open) || 0,
        high: parseFloat(candle.high) || 0,
        low: parseFloat(candle.low) || 0,
        close: parseFloat(candle.close) || 0,
        volume: parseFloat(candle.volume) || 0,
        vwap: parseFloat(candle.vwap) || 0,
      }))

      updateChart()

      // Cập nhật challenge total value sau khi fetch data mới
      if (challengeActive && challengePositions.length > 0) {
        setTimeout(() => {
          const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
          if (lastCandle && lastCandle.close) {
            const currentPrice = parseFloat(lastCandle.close)
            // Lưu ý: currentPrice là nghìn VNĐ, challengeBalance là VNĐ, cần nhân 1000
            let positionsValue = 0
            challengePositions.forEach(pos => {
              const price = pos.symbol === symbol ? currentPrice : (pos.avg_price || currentPrice)
              positionsValue += pos.quantity * price * 1000 // Nhân 1000 để đổi từ nghìn VNĐ sang VNĐ
            })
            const newTotalValue = challengeBalance + positionsValue
            setChallengeTotalValue(newTotalValue)
          }
        }, 100)
      }

      setLoading(false)
    } catch (error) {
      console.error('Error fetching historical data:', error)
      setLoading(false)
    }
  }, [symbol, startDate, startTime, endDate, endTime, challengeActive, challengeStartDate, challengeCurrentDate, chartViewStartDate, updateChart, challengePositions, challengeBalance])

  // Fetch data khi symbol thay đổi hoặc khi không có date filter (real-time mode)
  useEffect(() => {
    // Chờ chart được khởi tạo - sử dụng timeout để đảm bảo chart đã sẵn sàng
    const timer = setTimeout(() => {
      if (!candlestickSeriesRef.current) {
        return
      }

      // Nếu đang expand chart (từ expandChartOnOrder), không fetch lại
      // KHÔNG reset flag ở đây, để flag được reset sau khi fetch xong trong expandChartOnOrder
      if (isExpandingChartRef.current) {
        return
      }

      // Nếu có date filter và không phải challenge mode, không auto-fetch
      // User phải click nút "Tìm kiếm"
      if ((startDate || endDate) && !challengeActive) {
        return
      }

      fetchChartData()
    }, 200) // Delay để đảm bảo chart đã được khởi tạo

    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, challengeActive]) // Loại bỏ candlestickSeriesRef khỏi dependencies

  // WebSocket connection - chỉ hoạt động trong LIVE mode (không có date filter)
  useEffect(() => {
    // Chỉ connect WebSocket khi không có date filter (realtime mode)
    // Không cần check chartMode vì chartMode được set trong fetchChartData (async)
    if (!startDate && !endDate && !challengeActive) {
      const wsClient = getWebSocketClient()
      wsClientRef.current = wsClient

      // Disconnect WebSocket cũ trước khi connect mới
      if (wsClient.ws && wsClient.ws.readyState === WebSocket.OPEN) {
        wsClient.disconnect()
      }

      console.log('Connecting WebSocket for realtime updates, symbol:', symbol)

      // Sử dụng token từ ref để tránh reconnect khi token thay đổi
      wsClient.connect(symbol, tokenRef.current).then(() => {
        console.log('WebSocket connected successfully')
        const unsubscribe = wsClient.subscribe((message) => {
          if (message.type === 'ohlc_update') {
            const candle = message.data

            // CHỐT CHẶN: Chỉ update nếu message trả về đúng symbol đang xem
            if (message.symbol === symbol) {
              console.log('Received OHLC update:', candle.time, candle.close)
              updateOrAppendCandle({
                time: candle.time,
                open: parseFloat(candle.open),
                high: parseFloat(candle.high),
                low: parseFloat(candle.low),
                close: parseFloat(candle.close),
                volume: parseFloat(candle.volume) || 0,
                vwap: parseFloat(candle.vwap) || 0,
              })
            } else {
              console.log('Ignoring OHLC update for different symbol:', message.symbol, 'Current:', symbol)
            }
          }
        })

        return () => unsubscribe()
      }).catch(error => {
        console.error('WebSocket connection error:', error)
      })
    } else {
      // Có date filter hoặc challenge mode, disconnect WebSocket nếu đang kết nối
      if (wsClientRef.current) {
        console.log('Disconnecting WebSocket (HISTORY mode or challenge active)')
        wsClientRef.current.disconnect()
        wsClientRef.current = null
      }
    }

    return () => {
      // Cleanup: disconnect khi component unmount hoặc dependencies thay đổi
      if (wsClientRef.current) {
        wsClientRef.current.disconnect()
        wsClientRef.current = null
      }
    }
  }, [symbol, startDate, endDate, challengeActive, updateOrAppendCandle])

  // Hàm helper để kiểm tra xem một ngày có phải là ngày giao dịch không (thứ 2-6)
  const isTradingDay = (date) => {
    const dayOfWeek = date.getDay() // 0 = Chủ nhật, 1 = Thứ 2, ..., 6 = Thứ 7
    return dayOfWeek >= 1 && dayOfWeek <= 5 // Thứ 2-6
  }

  // Hàm helper để tính ngày kết thúc chỉ tính các ngày giao dịch (thứ 2-6)
  const calculateEndDate = (startDate, numTradingDays) => {
    const end = new Date(startDate)
    let tradingDaysCount = 0
    let daysAdded = 0

    // Đếm các ngày giao dịch (bỏ qua thứ 7 và chủ nhật)
    while (tradingDaysCount < numTradingDays) {
      const checkDate = new Date(startDate)
      checkDate.setDate(startDate.getDate() + daysAdded)
      if (isTradingDay(checkDate)) {
        tradingDaysCount++
        if (tradingDaysCount === numTradingDays) {
          // Đã đủ số ngày giao dịch, set end date
          end.setTime(checkDate.getTime())
        }
      }
      daysAdded++
    }

    return end
  }

  // Hàm bắt đầu thử thách
  const handleStartChallenge = async () => {
    if (!challengeStartDate) return

    try {
      // KHÔNG reset balance thực tế - chỉ quản lý challenge balance ở frontend
      // Kết hợp date và time
      const startDateTime = `${challengeStartDate}T${challengeStartTime}:00`
      const start = new Date(startDateTime)
      const duration = parseInt(challengeDuration)

      // Tính ngày kết thúc chỉ tính các ngày giao dịch (thứ 2-6)
      const end = calculateEndDate(start, duration)

      // Tính ngày bắt đầu hiển thị chart (7 ngày trước ngày bắt đầu)
      const chartStart = new Date(start)
      chartStart.setDate(chartStart.getDate() - 7)

      setChallengeActive(true)
      setChallengeCurrentDate(challengeStartDate)
      setChallengeEndDate(end.toISOString().split('T')[0])
      setChartViewStartDate(chartStart.toISOString().split('T')[0])

      // Khởi tạo challenge balance và total value
      setChallengeBalance(challengeCapital)
      setChallengeTotalValue(challengeCapital)
      setChallengePositions([]) // Reset positions khi bắt đầu challenge mới

      // Set date filter để hiển thị chart
      setStartDate(chartStart.toISOString().split('T')[0])
      setStartTime('00:00')
      setEndDate(challengeStartDate)
      setEndTime(challengeStartTime)
      challengeCurrentTimeRef.current = challengeStartTime
    } catch (error) {
      console.error('Error starting challenge:', error)
      showModal('Lỗi', 'Không thể bắt đầu thử thách. Vui lòng thử lại.', 'error')
    }
  }

  // Hàm kết thúc thử thách và tính lãi lỗ
  const handleEndChallenge = async () => {
    try {
      // Tính lãi lỗ dựa trên challengeBalance + giá trị positions tại thời điểm kết thúc
      let portfolioValue = challengeBalance

      // Nếu có positions, tính lại total value với giá tại thời điểm kết thúc
      if (challengePositions.length > 0) {
        try {
          // Lấy giá tại thời điểm kết thúc từ API
          const endDateTime = `${challengeEndDate}T15:00:00+07:00`
          const priceResponse = await api.get(`/ohlc/historical?symbol=${symbol}&interval=1m&limit=1&end_time=${encodeURIComponent(endDateTime)}`)

          if (priceResponse.data.data && priceResponse.data.data.length > 0) {
            const lastPrice = parseFloat(priceResponse.data.data[priceResponse.data.data.length - 1].close)
            // Tính tổng giá trị positions
            // Lưu ý: lastPrice là nghìn VNĐ (từ ClickHouse), challengeBalance là VNĐ, cần nhân 1000
            const positionsValue = challengePositions.reduce((total, pos) => {
              // Nếu position là symbol hiện tại, dùng lastPrice (giá tại thời điểm kết thúc)
              // Nếu là symbol khác, dùng avg_price (giá trung bình đã mua)
              // TODO: Có thể cải thiện bằng cách fetch giá cho từng symbol riêng
              const price = pos.symbol === symbol ? lastPrice : (pos.avg_price || lastPrice)
              const posValue = pos.quantity * price * 1000 // Nhân 1000 để đổi từ nghìn VNĐ sang VNĐ
              return total + posValue
            }, 0)
            // Total value = cash balance + positions value
            portfolioValue = challengeBalance + positionsValue
          } else {
            // Nếu không lấy được giá, dùng challengeTotalValue
            portfolioValue = challengeTotalValue
          }
        } catch (error) {
          console.error('Error getting end price:', error)
          // Fallback: sử dụng challengeTotalValue hiện tại
          portfolioValue = challengeTotalValue
        }
      } else {
        // Nếu không có positions, total value = balance
        portfolioValue = challengeBalance
      }

      const profit = portfolioValue - challengeCapital
      const profitPercent = ((profit / challengeCapital) * 100).toFixed(2)

      const resultMessage = `Vốn ban đầu: ${challengeCapital.toLocaleString('vi-VN')} VNĐ\nGiá trị hiện tại: ${portfolioValue.toLocaleString('vi-VN')} VNĐ\nLãi/Lỗ: ${profit >= 0 ? '+' : ''}${profit.toLocaleString('vi-VN')} VNĐ (${profitPercent}%)`
      showModal('Thử thách kết thúc!', resultMessage, profit >= 0 ? 'success' : 'error')

      // Reset challenge
      setChallengeActive(false)
      setChallengeStartDate('')
      setChallengeStartTime('09:00')
      setChallengeCurrentDate('')
      setChallengeEndDate('')
      setChartViewStartDate('')
      setChallengeBalance(challengeCapital)
      setChallengeTotalValue(challengeCapital)
      setChallengePositions([]) // Reset positions khi kết thúc challenge
      setStartDate('')
      setStartTime('00:00')
      setEndDate('')
      setEndTime('23:59')
      challengeCurrentTimeRef.current = '23:59'

      // Refresh portfolio để hiển thị lại số dư thực tế
      const portfolioResponse = await api.get('/portfolio/summary')
      if (portfolioResponse.data) {
        setPortfolio(portfolioResponse.data.portfolio)
        setPositions(portfolioResponse.data.positions || [])
      } else {
        // Fallback
        const fallbackResponse = await api.get('/portfolio')
        setPortfolio(fallbackResponse.data)
        setPositions([])
      }
    } catch (error) {
      console.error('Error ending challenge:', error)
      showModal('Lỗi', `Có lỗi xảy ra khi kết thúc thử thách: ${error.response?.data?.detail || error.message}`, 'error')
    }
  }

  // Hàm đặt lệnh
  const handleSubmitOrder = async (sideOverride = null) => {
    try {
      // Sử dụng sideOverride nếu có, nếu không thì dùng orderSide hiện tại
      const currentSide = sideOverride || orderSide

      if (!orderQuantity || parseInt(orderQuantity) === 0) {
        showModal('Thông báo', 'Vui lòng nhập số lượng', 'warning')
        return
      }

      // CHALLENGE MODE: Bỏ qua các kiểm tra orderType và session
      if (!challengeActive) {
        // Chỉ yêu cầu giá khi là lệnh LIMIT (LO) trong realtime mode
        if (orderType === 'LIMIT' && !orderPrice) {
          showModal('Thông báo', 'Vui lòng nhập giá', 'warning')
          return
        }

        // Kiểm tra số dư trước khi đặt lệnh MUA (realtime mode)
        if (currentSide === 'BUY') {
          const availableBalance = portfolio ? parseFloat(portfolio.cash_balance || 0) : 0
          const quantity = parseInt(orderQuantity)
          let requiredAmount = 0

          if (orderType === 'MARKET') {
            const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
            if (lastCandle && lastCandle.close) {
              requiredAmount = parseFloat(lastCandle.close) * quantity * 1000
            } else {
              showModal('Lỗi', 'Không thể lấy giá hiện tại. Vui lòng thử lại.', 'error')
              return
            }
          } else if (orderType === 'LIMIT') {
            requiredAmount = parseFloat(orderPrice) * quantity * 1000
          } else if (orderType === 'MTL') {
            const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
            if (lastCandle && lastCandle.close) {
              requiredAmount = parseFloat(lastCandle.close) * quantity * 1000
            } else {
              showModal('Lỗi', 'Không thể lấy giá hiện tại. Vui lòng thử lại.', 'error')
              return
            }
          } else {
            const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
            if (lastCandle && lastCandle.close) {
              requiredAmount = parseFloat(lastCandle.close) * quantity * 1000
            } else {
              showModal('Lỗi', 'Không thể lấy giá hiện tại. Vui lòng thử lại.', 'error')
              return
            }
          }

          if (requiredAmount > availableBalance) {
            const insufficientMessage = `Cần: ${requiredAmount.toLocaleString('vi-VN')} VNĐ\nCó: ${availableBalance.toLocaleString('vi-VN')} VNĐ\nThiếu: ${(requiredAmount - availableBalance).toLocaleString('vi-VN')} VNĐ`
            showModal('Số dư không đủ', insufficientMessage, 'error')
            return
          }
        } else if (currentSide === 'SELL') {
          // Kiểm tra số lượng khi BÁN (realtime mode)
          const quantity = parseInt(orderQuantity)
          const existing = positions.find(p => p.symbol === symbol)

          if (!existing) {
            showModal('Lỗi', 'Bạn chưa có cổ phiếu này để bán', 'error')
            setOrderSubmitting(false)
            return
          }

          if (existing.quantity < quantity) {
            showModal('Lỗi', `Số lượng chứng khoán không đủ. Bạn có ${existing.quantity} cổ, cần ${quantity} cổ`, 'error')
            setOrderSubmitting(false)
            return
          }
        }

        // Kiểm tra phiên giao dịch (realtime mode)
        const session = getCurrentSession()

        // Xử lý ATO: Lưu vào DB, sẽ khớp sau 09:15
        if (orderType === 'ATO') {
          if (session !== 'ATO_SESSION') {
            showModal('Lỗi', 'Lệnh ATO chỉ dùng được trong phiên mở cửa (09:00-09:15)', 'error')
            setOrderSubmitting(false)
            return
          }

          try {
            // Gọi API để lưu ATO vào DB
            const orderData = {
              symbol,
              side: currentSide,
              order_type: 'ATO',
              quantity: parseInt(orderQuantity),
              trading_mode: 'REALTIME'
            }

            const response = await api.post('/portfolio/orders', orderData)
            const savedOrder = response.data

            // Cập nhật pendingOrders state với order từ DB
            const pendingOrder = {
              id: savedOrder.id,
              symbol: savedOrder.symbol,
              side: savedOrder.side,
              orderType: savedOrder.order_type,
              quantity: savedOrder.quantity,
              status: savedOrder.status,
              targetTime: '09:15',
              targetDate: new Date().toISOString().split('T')[0], // YYYY-MM-DD
              createdAt: savedOrder.created_at
            }
            setPendingOrders(prev => [...prev, pendingOrder])

            showModal('Thông báo', 'Lệnh ATO đã được ghi nhận và sẽ khớp sau 09:15 dựa trên giá mở cửa', 'info')
            setOrderQuantity('')
            setOrderPrice('')
            setOrderSubmitting(false)
            return
          } catch (error) {
            console.error('Error creating ATO order:', error)
            showModal('Lỗi', `Không thể tạo lệnh ATO: ${error.response?.data?.detail || error.message}`, 'error')
            setOrderSubmitting(false)
            return
          }
        }

        // Xử lý ATC: Lưu vào DB, sẽ khớp sau 14:45
        if (orderType === 'ATC') {
          try {
            // Gọi API để lưu ATC vào DB
            const orderData = {
              symbol,
              side: currentSide,
              order_type: 'ATC',
              quantity: parseInt(orderQuantity),
              trading_mode: 'REALTIME'
            }

            const response = await api.post('/portfolio/orders', orderData)
            const savedOrder = response.data

            // Cập nhật pendingOrders state với order từ DB
            const pendingOrder = {
              id: savedOrder.id,
              symbol: savedOrder.symbol,
              side: savedOrder.side,
              orderType: savedOrder.order_type,
              quantity: savedOrder.quantity,
              status: savedOrder.status,
              targetTime: '14:45',
              targetDate: new Date().toISOString().split('T')[0], // YYYY-MM-DD
              createdAt: savedOrder.created_at
            }
            setPendingOrders(prev => [...prev, pendingOrder])

            if (session === 'CONTINUOUS_SESSION') {
              showModal('Thông báo', 'Lệnh ATC đã được ghi nhận và sẽ chờ khớp sau 14:45 dựa trên giá đóng cửa', 'info')
            } else if (session === 'ATC_SESSION') {
              showModal('Thông báo', 'Lệnh ATC đã được ghi nhận và sẽ khớp sau 14:45 dựa trên giá đóng cửa', 'info')
            } else {
              showModal('Thông báo', 'Lệnh ATC đã được ghi nhận và sẽ khớp sau 14:45 dựa trên giá đóng cửa', 'info')
            }

            setOrderQuantity('')
            setOrderPrice('')
            setOrderSubmitting(false)
            return
          } catch (error) {
            console.error('Error creating ATC order:', error)
            showModal('Lỗi', `Không thể tạo lệnh ATC: ${error.response?.data?.detail || error.message}`, 'error')
            setOrderSubmitting(false)
            return
          }
        }
      } else {
        // CHALLENGE MODE: Kiểm tra số dư và số lượng đơn giản
        if (currentSide === 'BUY') {
          const quantity = parseInt(orderQuantity)
          const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
          if (lastCandle && lastCandle.close) {
            const requiredAmount = parseFloat(lastCandle.close) * quantity * 1000
            if (requiredAmount > challengeBalance) {
              const insufficientMessage = `Cần: ${requiredAmount.toLocaleString('vi-VN')} VNĐ\nCó: ${challengeBalance.toLocaleString('vi-VN')} VNĐ\nThiếu: ${(requiredAmount - challengeBalance).toLocaleString('vi-VN')} VNĐ`
              showModal('Số dư không đủ', insufficientMessage, 'error')
              setOrderSubmitting(false)
              return
            }
          }
        } else if (currentSide === 'SELL') {
          const quantity = parseInt(orderQuantity)
          const existing = challengePositions.find(p => p.symbol === symbol)

          if (!existing) {
            showModal('Lỗi', 'Bạn chưa có cổ phiếu này để bán', 'error')
            setOrderSubmitting(false)
            return
          }

          if (existing.quantity < quantity) {
            showModal('Lỗi', `Số lượng chứng khoán không đủ. Bạn có ${existing.quantity} cổ, cần ${quantity} cổ`, 'error')
            setOrderSubmitting(false)
            return
          }
        }
      }

      setOrderSubmitting(true)

      // CHALLENGE MODE: Xử lý local, không gọi API - Tất cả lệnh đều khớp ngay
      if (challengeActive) {
        // Lấy giá mới nhất từ chart (giá close của candle cuối cùng)
        const getPriceAtSimulatedTime = () => {
          if (historicalCandlesRef.current.length === 0) return null

          // Sắp xếp mảng để đảm bảo nến cuối là nến mới nhất theo thời gian
          const sorted = [...historicalCandlesRef.current].sort((a, b) => {
            const timeA = typeof a.time === 'string' ? new Date(a.time).getTime() : (a.time > 1e12 ? a.time : a.time * 1000)
            const timeB = typeof b.time === 'string' ? new Date(b.time).getTime() : (b.time > 1e12 ? b.time : b.time * 1000)
            return timeA - timeB
          })
          const latest = sorted[sorted.length - 1]
          return latest ? parseFloat(latest.close) : null
        }

        const fillPrice = getPriceAtSimulatedTime()

        if (!fillPrice || isNaN(fillPrice) || fillPrice <= 0) {
          showModal('Lỗi', 'Không thể lấy giá hiện tại. Vui lòng thử lại.', 'error')
          setOrderSubmitting(false)
          return
        }

        const totalQuantity = parseInt(orderQuantity)
        const orderSymbol = symbol

        // Tất cả lệnh đều khớp ngay 100%
        const fillQuantity = totalQuantity
        // Giá từ ClickHouse là nghìn VNĐ
        // totalCost cho tính toán avg_price (không nhân 1000, vì avg_price lưu ở đơn vị nghìn VNĐ)
        const totalCostForAvgPrice = fillPrice * fillQuantity
        // totalCost cho trừ tiền (nhân 1000, vì balance lưu ở đơn vị VNĐ)
        const totalCostForBalance = fillPrice * fillQuantity * 1000

        // Tính toán positions mới
        let updatedPositions = [...challengePositions]
        let newBalance = challengeBalance

        if (currentSide === 'BUY') {
          // Trừ tiền khi mua (dùng totalCostForBalance)
          newBalance = challengeBalance - totalCostForBalance

          // Cập nhật positions: thêm hoặc cập nhật số lượng
          const existing = updatedPositions.find(p => p.symbol === orderSymbol)
          if (existing) {
            // Cập nhật position hiện có: tính lại giá trung bình
            // Công thức: Giá TB mới = (Tổng chi phí cũ + Tổng chi phí mới) / (Số lượng cũ + Số lượng mới)
            // Ví dụ: Đã có 100 cổ @ 20.0, mua thêm 50 cổ @ 25.0
            //   totalCostOld = 20.0 * 100 = 2000
            //   totalCostForAvgPrice = 25.0 * 50 = 1250
            //   newAvgPrice = (2000 + 1250) / (100 + 50) = 21.67
            // avg_price lưu ở đơn vị nghìn VNĐ, nên không nhân 1000
            const totalQuantity = existing.quantity + fillQuantity
            const totalCostOld = existing.avg_price * existing.quantity // Tổng chi phí cũ
            const totalCostNew = totalCostForAvgPrice // Tổng chi phí mới (fillPrice * fillQuantity)
            const newAvgPrice = (totalCostOld + totalCostNew) / totalQuantity
            updatedPositions = updatedPositions.map(p =>
              p.symbol === orderSymbol
                ? { ...p, quantity: totalQuantity, avg_price: newAvgPrice }
                : p
            )
          } else {
            // Thêm position mới
            updatedPositions = [...updatedPositions, { symbol: orderSymbol, quantity: fillQuantity, avg_price: fillPrice }]
          }
        } else if (currentSide === 'SELL') {
          // SELL: Kiểm tra số lượng trước
          const existing = updatedPositions.find(p => p.symbol === orderSymbol)
          if (!existing) {
            showModal('Lỗi', 'Bạn chưa có cổ phiếu này để bán', 'error')
            setOrderSubmitting(false)
            return
          }
          if (existing.quantity < fillQuantity) {
            showModal('Lỗi', `Số lượng chứng khoán không đủ. Bạn có ${existing.quantity} cổ, cần ${fillQuantity} cổ`, 'error')
            setOrderSubmitting(false)
            return
          }

          // Cộng tiền khi bán (dùng totalCostForBalance)
          newBalance = challengeBalance + totalCostForBalance

          // Cập nhật positions: trừ số lượng
          const newQuantity = existing.quantity - fillQuantity
          if (newQuantity <= 0) {
            // Xóa position nếu đã bán hết
            updatedPositions = updatedPositions.filter(p => p.symbol !== orderSymbol)
          } else {
            // Giữ nguyên giá trung bình, chỉ giảm số lượng
            updatedPositions = updatedPositions.map(p =>
              p.symbol === orderSymbol
                ? { ...p, quantity: newQuantity }
                : p
            )
          }
        } else {
          showModal('Lỗi', 'Loại lệnh không hợp lệ', 'error')
          setOrderSubmitting(false)
          return
        }

        // Cập nhật state
        setChallengeBalance(newBalance)
        setChallengePositions(updatedPositions)

        // Tính total value
        // Lưu ý: fillPrice là nghìn VNĐ, newBalance là VNĐ, cần nhân 1000 khi tính positionsValue
        const positionsValue = updatedPositions.reduce((total, pos) => {
          // Nếu position là symbol hiện tại, dùng fillPrice (giá vừa khớp)
          // Nếu là symbol khác, dùng avg_price (giá trung bình đã mua)
          const price = pos.symbol === orderSymbol ? fillPrice : (pos.avg_price || fillPrice)
          const posValue = pos.quantity * price * 1000 // Nhân 1000 để đổi từ nghìn VNĐ sang VNĐ
          return total + posValue
        }, 0)
        const newTotalValue = newBalance + positionsValue
        setChallengeTotalValue(newTotalValue)

        // Hiển thị thông báo thành công
        // fillPrice là nghìn VNĐ, cần nhân 1000 để hiển thị đúng
        const displayPrice = fillPrice * 1000
        const successMessage = `Đã khớp: ${fillQuantity} @ ${displayPrice.toLocaleString('vi-VN')} VNĐ`

        showModal('Đặt lệnh thành công', successMessage, 'success')

        // Reset form
        setOrderQuantity('')

        setOrderSubmitting(false)
        return
      }

      // REALTIME MODE: Gọi API
      // Backend chỉ chấp nhận MARKET hoặc LIMIT, nên MTL sẽ được gửi như MARKET
      // ATO và ATC đã được xử lý ở trên, không đến đây
      const orderData = {
        symbol: symbol,
        side: currentSide,
        order_type: orderType === 'MTL' ? 'MARKET' : orderType, // MTL gửi như MARKET
        quantity: parseInt(orderQuantity),
        trading_mode: 'REALTIME',
      }

      // Thêm price nếu là LIMIT order
      if (orderType === 'LIMIT') {
        orderData.price = parseFloat(orderPrice)
      }
      // MTL không cần gửi price vì đã gửi như MARKET, backend sẽ tự lấy giá thị trường

      const response = await api.post('/portfolio/orders', orderData)

      const successMessage = `Trạng thái: ${response.data.status}${response.data.filled_quantity > 0 ? `\nĐã khớp: ${response.data.filled_quantity} @ ${response.data.filled_price}` : ''}`
      showModal('Đặt lệnh thành công', successMessage, 'success')

      // Reset form
      setOrderQuantity('')
      setOrderPrice('')

      // Refresh portfolio
      const portfolioResponse = await api.get('/portfolio/summary')
      if (portfolioResponse.data) {
        setPortfolio(portfolioResponse.data.portfolio)
        setPositions(portfolioResponse.data.positions || [])
      } else {
        // Fallback
        const fallbackResponse = await api.get('/portfolio')
        setPortfolio(fallbackResponse.data)
        setPositions([])
      }
    } catch (error) {
      console.error('Error creating order:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Có lỗi xảy ra khi đặt lệnh'
      showModal('Lỗi', errorMessage, 'error')
    } finally {
      setOrderSubmitting(false)
    }
  }

  // Hàm mở rộng chart khi chọn bước nhảy
  const expandChartOnOrder = useCallback((selectedStep = null) => {
    if (!challengeActive || !challengeCurrentDate || !selectedStep) {
      console.warn('Cannot expand chart:', { challengeActive, challengeCurrentDate, selectedStep })
      return
    }

    console.log('Starting expandChartOnOrder with step:', selectedStep)

    const current = new Date(challengeCurrentDate)
    let newDate = new Date(current)
    let newEndTime = '23:59'

    // Lấy thời gian hiện tại từ endTime hoặc từ candle cuối cùng
    let currentTimeMinutes = 9 * 60 // Mặc định 9:00
    let currentHour = 9
    let currentMinute = 0

    // Ưu tiên lấy từ challengeCurrentTimeRef (thời gian hiện tại đã được lưu)
    // Nếu ref chưa có giá trị, lấy từ endTime
    const currentTimeStr = challengeCurrentTimeRef.current || endTime || '09:00'
    if (currentTimeStr) {
      const [hour, minute] = currentTimeStr.split(':').map(Number)
      if (!isNaN(hour) && !isNaN(minute)) {
        currentTimeMinutes = hour * 60 + minute
        currentHour = hour
        currentMinute = minute
      }
    } else {
      // Fallback: lấy từ candle cuối cùng
      const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
      if (lastCandle && lastCandle.time) {
        // Parse time từ candle (có thể là string hoặc timestamp)
        let timeStr = ''
        if (typeof lastCandle.time === 'string') {
          // Format: "2025-12-19T14:45:00" hoặc "14:45:00"
          if (lastCandle.time.includes('T')) {
            timeStr = lastCandle.time.split('T')[1]?.split('.')[0] || ''
          } else {
            timeStr = lastCandle.time
          }
        } else if (typeof lastCandle.time === 'number') {
          // Timestamp (seconds hoặc milliseconds)
          const date = new Date(lastCandle.time > 1e12 ? lastCandle.time : lastCandle.time * 1000)
          const hours = String(date.getUTCHours()).padStart(2, '0')
          const minutes = String(date.getUTCMinutes()).padStart(2, '0')
          timeStr = `${hours}:${minutes}:00`
        }

        if (timeStr) {
          const [hour, minute] = timeStr.split(':').map(Number)
          if (!isNaN(hour) && !isNaN(minute)) {
            currentTimeMinutes = hour * 60 + minute
            currentHour = hour
            currentMinute = minute
          }
        }
      }
    }

    console.log('Current time:', { currentHour, currentMinute, currentTimeMinutes, endTime })

    // Hàm helper để điều chỉnh thời gian sau khi nhảy (skip khoảng nghỉ trưa và cuối phiên)
    const adjustTimeAfterJump = (hour, minute, date) => {
      let adjustedHour = hour
      let adjustedMinute = minute
      let adjustedDate = new Date(date)

      // Tính thời gian dưới dạng phút để dễ so sánh
      const timeInMinutes = adjustedHour * 60 + adjustedMinute

      // Nếu rơi vào khoảng nghỉ trưa (11:30 - 12:59), nhảy đến 13:00
      if (timeInMinutes >= 11 * 60 + 30 && timeInMinutes < 13 * 60) {
        adjustedHour = 13
        adjustedMinute = 0
        console.log('Skipping lunch break, jumping to 13:00')
      }
      // Nếu vượt quá cuối phiên chiều (sau 14:45), nhảy sang ngày giao dịch tiếp theo và bắt đầu từ 9:00
      else if (timeInMinutes > 14 * 60 + 45) {
        // Tìm ngày giao dịch tiếp theo (bỏ qua thứ 7 và chủ nhật)
        let nextTradingDay = new Date(adjustedDate)
        nextTradingDay.setDate(nextTradingDay.getDate() + 1)
        while (!isTradingDay(nextTradingDay)) {
          nextTradingDay.setDate(nextTradingDay.getDate() + 1)
        }
        adjustedDate = nextTradingDay
        adjustedHour = 9
        adjustedMinute = 0
        console.log('Exceeded afternoon session, jumping to next trading day 9:00')
      }
      // Nếu đúng 14:45 (cuối phiên chiều), nhảy sang ngày giao dịch tiếp theo và bắt đầu từ 9:00 hoặc 9:15
      else if (timeInMinutes === 14 * 60 + 45) {
        // Tìm ngày giao dịch tiếp theo (bỏ qua thứ 7 và chủ nhật)
        let nextTradingDay = new Date(adjustedDate)
        nextTradingDay.setDate(nextTradingDay.getDate() + 1)
        while (!isTradingDay(nextTradingDay)) {
          nextTradingDay.setDate(nextTradingDay.getDate() + 1)
        }
        adjustedDate = nextTradingDay
        // Bắt đầu từ 9:00 (có thể thay đổi thành 9:15 nếu cần)
        adjustedHour = 9
        adjustedMinute = 0
        console.log('End of afternoon session, jumping to next trading day 9:00')
      }
      // Nếu trước 9:00, nhảy đến 9:00
      else if (timeInMinutes < 9 * 60) {
        adjustedHour = 9
        adjustedMinute = 0
        console.log('Before market open, jumping to 9:00')
      }

      return { adjustedHour, adjustedMinute, adjustedDate }
    }

    // Xử lý các bước nhảy mới
    if (selectedStep === '1p') {
      // Nhảy 1 phút
      currentMinute += 1
      if (currentMinute >= 60) {
        currentMinute = 0
        currentHour += 1
        if (currentHour >= 24) {
          currentHour = 0
          newDate.setDate(newDate.getDate() + 1)
        }
      }
      const adjusted = adjustTimeAfterJump(currentHour, currentMinute, newDate)
      currentHour = adjusted.adjustedHour
      currentMinute = adjusted.adjustedMinute
      newDate = adjusted.adjustedDate
      newEndTime = `${String(currentHour).padStart(2, '0')}:${String(currentMinute).padStart(2, '0')}`
    } else if (selectedStep === '5p') {
      // Nhảy 5 phút
      currentMinute += 5
      if (currentMinute >= 60) {
        currentMinute = currentMinute - 60
        currentHour += 1
        if (currentHour >= 24) {
          currentHour = 0
          newDate.setDate(newDate.getDate() + 1)
        }
      }
      const adjusted = adjustTimeAfterJump(currentHour, currentMinute, newDate)
      currentHour = adjusted.adjustedHour
      currentMinute = adjusted.adjustedMinute
      newDate = adjusted.adjustedDate
      newEndTime = `${String(currentHour).padStart(2, '0')}:${String(currentMinute).padStart(2, '0')}`
    } else if (selectedStep === '30p') {
      // Nhảy 30 phút
      currentMinute += 30
      if (currentMinute >= 60) {
        currentMinute = currentMinute - 60
        currentHour += 1
        if (currentHour >= 24) {
          currentHour = 0
          newDate.setDate(newDate.getDate() + 1)
        }
      }
      const adjusted = adjustTimeAfterJump(currentHour, currentMinute, newDate)
      currentHour = adjusted.adjustedHour
      currentMinute = adjusted.adjustedMinute
      newDate = adjusted.adjustedDate
      newEndTime = `${String(currentHour).padStart(2, '0')}:${String(currentMinute).padStart(2, '0')}`
    } else if (selectedStep === '1h') {
      // Nhảy 1 giờ
      currentHour += 1
      if (currentHour >= 24) {
        currentHour = 0
        newDate.setDate(newDate.getDate() + 1)
      }
      const adjusted = adjustTimeAfterJump(currentHour, currentMinute, newDate)
      currentHour = adjusted.adjustedHour
      currentMinute = adjusted.adjustedMinute
      newDate = adjusted.adjustedDate
      newEndTime = `${String(currentHour).padStart(2, '0')}:${String(currentMinute).padStart(2, '0')}`
    } else if (selectedStep === '1d') {
      // Nhảy 1 ngày - bắt đầu từ 9:00 ngày mới
      newDate.setDate(newDate.getDate() + 1)
      newEndTime = '09:00'
    } else {
      // Không nhận diện được bước nhảy
      return
    }

    // Không vượt quá ngày kết thúc
    const endDateObj = new Date(challengeEndDate)
    if (newDate > endDateObj) {
      newDate.setTime(endDateObj.getTime())
      // Nếu đã đến ngày kết thúc, đặt thời gian là cuối phiên chiều (14:45)
      newEndTime = '14:45'
    }

    const newDateStr = newDate.toISOString().split('T')[0]
    // Nếu là ngày bắt đầu và endTime là 09:00, dùng challengeStartTime
    if (newDateStr === challengeStartDate && newEndTime === '09:00') {
      newEndTime = challengeStartTime
    }

    console.log('Calculated new time:', {
      oldDate: challengeCurrentDate,
      oldTime: endTime,
      newDateStr,
      newEndTime,
      selectedStep
    })

    // QUAN TRỌNG: Cập nhật ref NGAY LẬP TỨC để lần nhảy tiếp theo có thể dùng giá trị mới
    // Ref được cập nhật đồng bộ, không phải async như state
    challengeCurrentTimeRef.current = newEndTime

    // Cập nhật state để UI hiển thị đúng
    setChallengeCurrentDate(newDateStr)
    setEndDate(newDateStr)
    setEndTime(newEndTime)

    // Set flag để tránh useEffect trigger fetch lại
    // QUAN TRỌNG: Set flag TRƯỚC khi update state để các useEffect có thể check flag
    isExpandingChartRef.current = true

    // Fetch lại chart data với ngày mới ngay lập tức (TRƯỚC khi update state)
    // Sử dụng giá trị mới trực tiếp thay vì đợi state update
    // QUAN TRỌNG: Luôn fetch lại ngay cả khi cùng ngày (ví dụ: từ 9:45 -> 11:30)
    if (challengeActive && chartViewStartDate) {
      const actualStartDate = chartViewStartDate
      const actualStartTime = '00:00'
      const actualEndDate = newDateStr
      const actualEndTime = newEndTime

      console.log('Expanding chart:', {
        actualStartDate,
        actualEndDate,
        actualEndTime,
        currentDate: challengeCurrentDate,
        newDateStr,
        selectedStep
      })

      // Build query params
      let url = `/ohlc/historical?symbol=${symbol}&interval=1m&limit=10000`
      if (actualStartDate) {
        const startDateTime = `${actualStartDate}T${actualStartTime}:00+07:00`
        url += `&start_time=${encodeURIComponent(startDateTime)}`
      }
      if (actualEndDate) {
        const endTimeParts = actualEndTime.split(':')
        const endTimeFormatted = endTimeParts.length === 2 ? `${actualEndTime}:00` : actualEndTime
        const endDateTime = `${actualEndDate}T${endTimeFormatted}+07:00`
        url += `&end_time=${encodeURIComponent(endDateTime)}`
      }

      console.log('Fetching chart data with URL:', url)

      // Fetch data mới (chỉ từ thời điểm hiện tại đến thời điểm mới)
      // Thay vì fetch lại toàn bộ, chỉ fetch phần mới để append vào chart
      const currentTimeStr = challengeCurrentTimeRef.current || endTime || '09:00'
      const [currentHour, currentMinute] = currentTimeStr.split(':').map(Number)
      const currentDateTime = `${challengeCurrentDate}T${String(currentHour).padStart(2, '0')}:${String(currentMinute).padStart(2, '0')}:00+07:00`

      // Fetch chỉ data mới từ thời điểm hiện tại đến thời điểm mới
      let incrementalUrl = `/ohlc/historical?symbol=${symbol}&interval=1m&limit=10000`
      incrementalUrl += `&start_time=${encodeURIComponent(currentDateTime)}`
      const endTimeParts = newEndTime.split(':')
      const endTimeFormatted = endTimeParts.length === 2 ? `${newEndTime}:00` : newEndTime
      const endDateTime = `${newDateStr}T${endTimeFormatted}+07:00`
      incrementalUrl += `&end_time=${encodeURIComponent(endDateTime)}`

      console.log('Fetching incremental data:', incrementalUrl)

      api.get(incrementalUrl).then(response => {
        console.log('Incremental chart data response:', response.data.data?.length, 'candles')
        if (response.data.data && response.data.data.length > 0) {
          // Helper để normalize time
          const normalizeTime = (time) => {
            if (typeof time === 'string') {
              const hasTimezone = time.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(time)
              if (!hasTimezone) {
                const dtVN = new Date(time + '+07:00')
                return (dtVN.getTime() + 7 * 3600000) / 1000
              }
              return Math.floor(new Date(time).getTime() / 1000)
            }
            return time > 1e12 ? Math.floor(time / 1000) : time
          }

          // Append các candle mới vào chart (không reset)
          response.data.data.forEach(c => {
            const candle = {
              time: c.time,
              open: parseFloat(c.open) || 0,
              high: parseFloat(c.high) || 0,
              low: parseFloat(c.low) || 0,
              close: parseFloat(c.close) || 0,
              volume: parseFloat(c.volume) || 0,
              vwap: parseFloat(c.vwap) || 0
            }

            const timestamp = normalizeTime(candle.time)

            // Kiểm tra xem candle đã tồn tại chưa
            const existingIndex = historicalCandlesRef.current.findIndex(existing => {
              const existingTime = normalizeTime(existing.time)
              return Math.abs(existingTime - timestamp) < 60 // Trong vòng 1 phút
            })

            if (existingIndex !== -1) {
              // Update candle hiện có
              historicalCandlesRef.current[existingIndex] = candle

              // Update trên chart
              if (candlestickSeriesRef.current) {
                candlestickSeriesRef.current.update({
                  time: timestamp,
                  open: candle.open,
                  high: candle.high,
                  low: candle.low,
                  close: candle.close
                })
              }

              if (volumeSeriesRef.current) {
                volumeSeriesRef.current.update({
                  time: timestamp,
                  value: candle.volume,
                  color: candle.close >= candle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                })
              }

              if (vwapSeriesRef.current && candle.vwap) {
                vwapSeriesRef.current.update({
                  time: timestamp,
                  value: candle.vwap
                })
              }
            } else {
              // Append candle mới
              historicalCandlesRef.current.push(candle)

              // Append vào chart series
              if (candlestickSeriesRef.current) {
                candlestickSeriesRef.current.update({
                  time: timestamp,
                  open: candle.open,
                  high: candle.high,
                  low: candle.low,
                  close: candle.close
                })
              }

              if (volumeSeriesRef.current) {
                volumeSeriesRef.current.update({
                  time: timestamp,
                  value: candle.volume,
                  color: candle.close >= candle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                })
              }

              if (vwapSeriesRef.current && candle.vwap) {
                vwapSeriesRef.current.update({
                  time: timestamp,
                  value: candle.vwap
                })
              }
            }
          })

          // Cập nhật legend với candle cuối cùng
          const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
          if (lastCandle) {
            setLegendData({
              open: parseFloat(lastCandle.open).toFixed(2),
              high: parseFloat(lastCandle.high).toFixed(2),
              low: parseFloat(lastCandle.low).toFixed(2),
              close: parseFloat(lastCandle.close).toFixed(2),
              volume: (lastCandle.volume || 0).toLocaleString(),
            })
          }

          console.log('Appended incremental data, total candles:', historicalCandlesRef.current.length)

          // Cập nhật challenge total value sau khi append data mới
          if (challengePositions.length > 0) {
            const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
            if (lastCandle && lastCandle.close) {
              const currentPrice = parseFloat(lastCandle.close)
              let positionsValue = 0
              challengePositions.forEach(pos => {
                const price = pos.symbol === symbol ? currentPrice : (pos.avg_price || currentPrice)
                positionsValue += pos.quantity * price * 1000
              })
              const newTotalValue = challengeBalance + positionsValue
              setChallengeTotalValue(newTotalValue)
            }
          }

          setLoading(false)
        } else {
          console.warn('No incremental data received from API')
          setLoading(false)
        }
      }).catch(error => {
        console.error('Error fetching incremental chart data after step:', error)
        setLoading(false)
        isExpandingChartRef.current = false
      }).finally(() => {
        // Reset flag sau khi đã append xong
        setTimeout(() => {
          isExpandingChartRef.current = false
          console.log('Reset isExpandingChartRef flag')
        }, 300)
      })
    } else {
      // Nếu không fetch, chỉ reset flag (state đã được cập nhật ở trên)
      console.warn('Cannot fetch incremental chart data: challengeActive or chartViewStartDate missing')
      setTimeout(() => {
        isExpandingChartRef.current = false
      }, 300)
    }
  }, [challengeActive, challengeCurrentDate, challengeEndDate, challengeStartDate, challengeStartTime, chartViewStartDate, symbol, challengePositions, challengeBalance, endTime])

  return (
    <div className="trading-page">
      <div className="page-header">
        <h1 className="page-title">Giao Dịch</h1>
        {/* Tạm ẩn AI Coach button
        <button
          className="ai-coach-toggle-btn"
          onClick={() => setAiCoachOpen(!aiCoachOpen)}
        >
          {aiCoachOpen ? 'Đóng AI Coach' : 'Mở AI Coach'}
        </button>
        */}
      </div>

      <div className="trading-controls">
        <div className="symbol-panel">
          <div className="symbol-panel-header">
            <h3 className="symbol-panel-title">Mã chứng khoán</h3>
            {symbol && (
              <div className="current-symbol-badge">
                <span className="badge-label">Đang xem:</span>
                <span className="badge-value">{symbol}</span>
              </div>
            )}
          </div>

          <div className="symbol-panel-content">
            <div className="symbol-search-section">
              <div className="symbol-search-container">
                <input
                  ref={searchInputRef}
                  id="symbol"
                  type="text"
                  value={isInputFocused ? searchTerm : symbol}
                  onChange={(e) => {
                    const value = e.target.value.toUpperCase()
                    setSearchTerm(value)
                    setShowSuggestions(true)

                    // Nếu value khớp với một symbol, tự động chọn
                    if (symbols.includes(value)) {
                      setSymbol(value)
                      setSearchTerm('')
                      setShowSuggestions(false)
                      setIsInputFocused(false)
                    }
                  }}
                  onFocus={() => {
                    setSearchTerm('')
                    setIsInputFocused(true)
                    setShowSuggestions(true)
                  }}
                  onBlur={(e) => {
                    // Delay để cho phép click vào suggestion
                    setTimeout(() => {
                      if (!suggestionsRef.current?.contains(document.activeElement)) {
                        setShowSuggestions(false)
                        setSearchTerm('')
                        setIsInputFocused(false)
                      }
                    }, 200)
                  }}
                  placeholder="Nhập mã CK để tìm kiếm..."
                  disabled={symbols.length === 0}
                  className="symbol-search-input"
                />
                {showSuggestions && symbols.length > 0 && (
                  <div
                    ref={suggestionsRef}
                    className="symbol-suggestions"
                  >
                    {symbols
                      .filter(s => s.includes(searchTerm.toUpperCase()) || !searchTerm)
                      .slice(0, 10) // Giới hạn 10 kết quả
                      .map(s => (
                        <div
                          key={s}
                          className={`suggestion-item ${s === symbol ? 'active' : ''}`}
                          onClick={() => {
                            setSymbol(s)
                            setSearchTerm('')
                            setShowSuggestions(false)
                            searchInputRef.current?.blur()
                          }}
                        >
                          {s}
                        </div>
                      ))}
                    {symbols.filter(s => s.includes(searchTerm.toUpperCase()) || !searchTerm).length === 0 && (
                      <div className="suggestion-item no-results">Không tìm thấy</div>
                    )}
                  </div>
                )}
              </div>

              {popularSymbols.length > 0 && (
                <div className="popular-symbols">
                  <div className="popular-symbols-header">
                    <span className="popular-symbols-label">Gợi ý nhanh:</span>
                    <span className="popular-symbols-note">(Những mã có nguồn dữ liệu đầy đủ)</span>
                  </div>
                  <div className="popular-symbols-list">
                    {popularSymbols.map(popSymbol => (
                      <button
                        key={popSymbol}
                        type="button"
                        className={`popular-symbol-btn ${popSymbol === symbol ? 'active' : ''}`}
                        onClick={() => {
                          setSymbol(popSymbol)
                          setSearchTerm('')
                          setShowSuggestions(false)
                        }}
                      >
                        {popSymbol}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Thông tin công ty */}
            {companyInfo && (
              <div className="company-info-panel">
                <div className="company-info-header">
                  <h4>Thông tin công ty</h4>
                </div>
                <div className="company-info-content">
                  {companyInfo.company_name && (
                    <div className="company-info-item highlight">
                      <span className="company-info-label">Tên công ty:</span>
                      <span className="company-info-value">{companyInfo.company_name}</span>
                    </div>
                  )}
                  <div className="company-info-grid">
                    {companyInfo.sector && (
                      <div className="company-info-item">
                        <span className="company-info-label">Ngành:</span>
                        <span className="company-info-value">{companyInfo.sector}</span>
                      </div>
                    )}
                    {companyInfo.industry && (
                      <div className="company-info-item">
                        <span className="company-info-label">Lĩnh vực:</span>
                        <span className="company-info-value">{companyInfo.industry}</span>
                      </div>
                    )}
                    {companyInfo.exchange && (
                      <div className="company-info-item">
                        <span className="company-info-label">Sàn:</span>
                        <span className="company-info-value">{companyInfo.exchange}</span>
                      </div>
                    )}
                    {companyInfo.lot_size && (
                      <div className="company-info-item">
                        <span className="company-info-label">Khối lượng lô:</span>
                        <span className="company-info-value">{companyInfo.lot_size}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="date-filter-wrapper">
          <div className="date-filter">
            <div className="date-filter-item">
              <label htmlFor="start-date">Ngày bắt đầu:</label>
              <div className="datetime-input-group">
                <input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="date-input"
                />
                <input
                  id="start-time"
                  type="time"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                  className="time-input"
                />
              </div>
            </div>
            <div className="date-filter-item">
              <label htmlFor="end-date">Ngày kết thúc:</label>
              <div className="datetime-input-group">
                <input
                  id="end-date"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="date-input"
                />
                <input
                  id="end-time"
                  type="time"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                  className="time-input"
                />
              </div>
            </div>
            <div className="date-filter-actions">
              <button
                onClick={() => fetchChartData()}
                className="search-date-btn"
                disabled={!startDate && !endDate}
              >
                Tìm kiếm
              </button>
              {(startDate || endDate) && (
                <button
                  onClick={() => {
                    setStartDate('')
                    setStartTime('00:00')
                    setEndDate('')
                    setEndTime('23:59')
                    challengeCurrentTimeRef.current = '23:59'
                  }}
                  className="clear-date-btn"
                >
                  Xóa bộ lọc
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="chart-and-panel-container">
        <div
          className="chart-container"
          ref={chartContainerRef}
          key={`${symbol}-${challengeActive}`}
        >
          {loading && <div className="chart-loading">Đang tải dữ liệu...</div>}
          <div className="chart-legend">
            <div>
              <span className="legend-symbol">{symbol}</span>
            </div>
            <span className="legend-item">O: <span className="legend-val">{legendData.open}</span></span>
            <span className="legend-item">H: <span className="legend-val">{legendData.high}</span></span>
            <span className="legend-item">L: <span className="legend-val">{legendData.low}</span></span>
            <span className="legend-item">C: <span className="legend-val">{legendData.close}</span></span>
            <span className="legend-item">V: <span className="legend-val">{legendData.volume}</span></span>
          </div>
        </div>

        <div className="trading-panel">
          {/* Order Form */}
          <div className="order-form">
            {challengeActive ? (
              /* Challenge Mode: Chỉ hiển thị số lượng và nút MUA/BÁN */
              <>
                {/* Symbol Input */}
                <div className="order-form-group">
                  <div className="symbol-input-wrapper">
                    <input
                      type="text"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                      className="order-input symbol-input"
                      placeholder="Nhập mã CK"
                    />
                    {symbol && (
                      <button
                        className="clear-symbol-btn"
                        onClick={() => setSymbol('')}
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>

                {/* Buying Power */}
                <div className="buying-power-group">
                  <label>Sức mua:</label>
                  <div className="buying-power-input">
                    <span>{challengeBalance.toLocaleString('vi-VN')} VNĐ</span>
                  </div>
                </div>

                {/* Quantity Input */}
                <div className="order-form-group">
                  <label htmlFor="order-quantity">KL đặt</label>
                  <div className="quantity-input-wrapper">
                    <div className="quantity-row">
                      <input
                        id="order-quantity"
                        type="number"
                        value={orderQuantity}
                        onChange={(e) => setOrderQuantity(e.target.value)}
                        className="order-input quantity-input"
                        placeholder="Nhập số lượng"
                        min="0"
                      />
                      <div className="quantity-buttons">
                        <button
                          className="btn-adjust"
                          onClick={() => {
                            const currentQty = parseInt(orderQuantity) || 0
                            if (currentQty > 0) {
                              setOrderQuantity((currentQty - 1).toString())
                            }
                          }}
                        >
                          −
                        </button>
                        <button
                          className="btn-adjust"
                          onClick={() => {
                            const currentQty = parseInt(orderQuantity) || 0
                            setOrderQuantity((currentQty + 1).toString())
                          }}
                        >
                          +
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Order Action Buttons */}
                <div className="order-action-buttons">
                  <button
                    className={`order-action-btn buy-btn ${orderSide === 'BUY' ? 'active' : ''}`}
                    onClick={() => {
                      setOrderSide('BUY')
                      handleSubmitOrder('BUY')
                    }}
                    disabled={orderSubmitting || !orderQuantity || parseInt(orderQuantity) === 0}
                  >
                    MUA
                  </button>
                  <button
                    className={`order-action-btn sell-btn ${orderSide === 'SELL' ? 'active' : ''}`}
                    onClick={() => {
                      setOrderSide('SELL')
                      handleSubmitOrder('SELL')
                    }}
                    disabled={orderSubmitting || !orderQuantity || parseInt(orderQuantity) === 0}
                  >
                    BÁN
                  </button>
                </div>

                {/* Bước nhảy thời gian - Chỉ hiển thị trong challenge mode */}
                <div className="challenge-time-step">
                  <label>Bước nhảy thời gian:</label>
                  <div className="step-buttons-grid">
                    <button
                      className="step-btn"
                      onClick={() => handleStepSelection('1p')}
                      title="Nhảy 1 phút"
                    >
                      +1p
                    </button>
                    <button
                      className="step-btn"
                      onClick={() => handleStepSelection('5p')}
                      title="Nhảy 5 phút"
                    >
                      +5p
                    </button>
                    <button
                      className="step-btn"
                      onClick={() => handleStepSelection('30p')}
                      title="Nhảy 30 phút"
                    >
                      +30p
                    </button>
                    <button
                      className="step-btn"
                      onClick={() => handleStepSelection('1h')}
                      title="Nhảy 1 giờ"
                    >
                      +1h
                    </button>
                    <button
                      className="step-btn"
                      onClick={() => handleStepSelection('1d')}
                      title="Nhảy 1 ngày"
                    >
                      +1d
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* Realtime Mode: Giữ nguyên UI cũ */
              <>
                {/* Symbol Input */}
                <div className="order-form-group">
                  <div className="symbol-input-wrapper">
                    <input
                      type="text"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                      className="order-input symbol-input"
                      placeholder="Nhập mã CK"
                    />
                    {symbol && (
                      <button
                        className="clear-symbol-btn"
                        onClick={() => setSymbol('')}
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>

                {/* Buying Power - Số tiền khả dụng */}
                <div className="buying-power-group">
                  <label>Sức mua:</label>
                  <div className="buying-power-input">
                    <span>{(portfolio ? parseFloat(portfolio.cash_balance || 0) : 0).toLocaleString('vi-VN')} VNĐ</span>
                    <button
                      className="btn-plus"
                      onClick={() => navigate('/exchange')}
                      title="Đổi sao lấy tiền"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Order Type Buttons */}
                <div className="order-type-buttons">
                  <button
                    className={`order-type-btn ${orderType === 'LIMIT' ? 'active' : ''}`}
                    onClick={() => {
                      setOrderType('LIMIT')
                      if (!orderPrice && historicalCandlesRef.current.length > 0) {
                        const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                        if (lastCandle && lastCandle.close) {
                          setOrderPrice(parseFloat(lastCandle.close).toString())
                        }
                      }
                    }}
                  >
                    LO
                  </button>
                  <button
                    className={`order-type-btn ${orderType === 'MTL' ? 'active' : ''}`}
                    onClick={() => {
                      setOrderType('MTL')
                      setOrderPrice('')
                    }}
                  >
                    MTL
                  </button>
                  {/* ATO/ATC chỉ hiển thị trong Realtime mode, không hiển thị trong Challenge mode */}
                  {!challengeActive && (() => {
                    const session = getCurrentSession()
                    const showATO = session === 'ATO_SESSION' || session === 'OUT_OF_MARKET'
                    return showATO ? (
                      <button
                        className={`order-type-btn ${orderType === 'ATO' ? 'active' : ''}`}
                        onClick={() => {
                          setOrderType('ATO')
                          setOrderPrice('')
                        }}
                      >
                        ATO
                      </button>
                    ) : null
                  })()}
                  {!challengeActive && (
                    <button
                      className={`order-type-btn ${orderType === 'ATC' ? 'active' : ''}`}
                      onClick={() => {
                        setOrderType('ATC')
                        setOrderPrice('')
                        const session = getCurrentSession()
                        if (session === 'CONTINUOUS_SESSION') {
                          showModal('Thông báo', 'Lệnh ATC sẽ được treo và chỉ khớp sau 14:45 dựa trên giá đóng cửa', 'info')
                        }
                      }}
                    >
                      ATC
                    </button>
                  )}
                </div>

                {/* Price Input - Chỉ hiển thị cho LO (LIMIT) */}
                {orderType === 'LIMIT' && (
                  <div className="order-form-group">
                    <label htmlFor="order-price">Giá đặt</label>
                    <div className="price-input-wrapper">
                      <input
                        id="order-price"
                        type="number"
                        value={orderPrice}
                        onChange={(e) => setOrderPrice(e.target.value)}
                        className="order-input price-input"
                        placeholder="Nhập giá"
                        min="0"
                        step="0.01"
                      />
                      <button
                        className="btn-match"
                        onClick={() => {
                          // Lấy giá khớp từ candle cuối cùng
                          const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                          if (lastCandle && lastCandle.close) {
                            setOrderPrice(parseFloat(lastCandle.close).toString())
                          }
                        }}
                      >
                        Khớp
                      </button>
                      <button
                        className="btn-adjust"
                        onClick={() => {
                          const currentPrice = parseFloat(orderPrice) || 0
                          const step = currentPrice >= 1000 ? 100 : (currentPrice >= 100 ? 10 : 1)
                          setOrderPrice((currentPrice - step).toString())
                        }}
                      >
                        −
                      </button>
                      <button
                        className="btn-adjust"
                        onClick={() => {
                          const currentPrice = parseFloat(orderPrice) || 0
                          const step = currentPrice >= 1000 ? 100 : (currentPrice >= 100 ? 10 : 1)
                          setOrderPrice((currentPrice + step).toString())
                        }}
                      >
                        +
                      </button>
                    </div>
                  </div>
                )}

                {/* Quantity Input */}
                <div className="order-form-group">
                  <label htmlFor="order-quantity">KL đặt</label>
                  <div className="quantity-input-wrapper">
                    <div className="quantity-row">
                      <input
                        id="order-quantity"
                        type="number"
                        value={orderQuantity}
                        onChange={(e) => setOrderQuantity(e.target.value)}
                        className="order-input quantity-input"
                        placeholder="Nhập số lượng"
                        min="0"
                      />
                      <div className="quantity-buttons">
                        <button
                          className="btn-adjust"
                          onClick={() => {
                            const currentQty = parseInt(orderQuantity) || 0
                            if (currentQty > 0) {
                              setOrderQuantity((currentQty - 1).toString())
                            }
                          }}
                        >
                          −
                        </button>
                        <button
                          className="btn-adjust"
                          onClick={() => {
                            const currentQty = parseInt(orderQuantity) || 0
                            setOrderQuantity((currentQty + 1).toString())
                          }}
                        >
                          +
                        </button>
                      </div>
                    </div>
                    {orderQuantity && parseInt(orderQuantity) === 0 && (
                      <span className="error-message">KL không hợp lệ</span>
                    )}
                  </div>
                </div>

                {/* Chỉ hiển thị chế độ khi không có challenge */}
                <div className="order-form-row">
                  <div className="order-form-group">
                    <label htmlFor="order-mode">Chế độ:</label>
                    <select
                      id="order-mode"
                      defaultValue="REALTIME"
                      className="order-select"
                      disabled
                    >
                      <option value="REALTIME">Real-time</option>
                    </select>
                    <span className="order-hint">Chế độ thực hành chỉ có trong Thử thách đầu tư</span>
                  </div>
                </div>

                {/* Ẩn nút đặt lệnh khi đang xem dữ liệu quá khứ */}
                {(() => {
                  const today = new Date().toISOString().split('T')[0]

                  // Realtime mode: chỉ ẩn khi có date filter VÀ endDate là quá khứ
                  if ((startDate || endDate) && endDate && endDate < today) {
                    return (
                      <div className="order-disabled-message">
                        <p>Không thể đặt lệnh khi đang xem dữ liệu quá khứ. Vui lòng chọn ngày hiện tại hoặc tương lai, hoặc bỏ date filter để xem realtime.</p>
                      </div>
                    )
                  }

                  // Tính giá trị lệnh
                  const calculateOrderValue = () => {
                    if (!orderQuantity || parseInt(orderQuantity) === 0) return 0
                    const qty = parseInt(orderQuantity)
                    let price = 0

                    if (orderType === 'LIMIT') {
                      price = parseFloat(orderPrice) || 0
                    } else if (orderType === 'MTL') {
                      // MTL: Lấy giá mới nhất từ chart
                      const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                      if (lastCandle && lastCandle.close) {
                        price = parseFloat(lastCandle.close)
                      }
                    } else {
                      // MARKET, ATO, ATC - lấy giá từ candle cuối cùng
                      const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                      if (lastCandle && lastCandle.close) {
                        price = parseFloat(lastCandle.close)
                      }
                    }

                    // Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000
                    return price * qty * 1000
                  }

                  const orderValue = calculateOrderValue()

                  // Tính số lượng tối đa có thể mua/bán
                  const calculateMaxQuantity = () => {
                    if (orderSide === 'BUY') {
                      const availableBalance = portfolio ? parseFloat(portfolio.cash_balance || 0) : 0
                      let price = 0

                      if (orderType === 'LIMIT') {
                        price = parseFloat(orderPrice) || 0
                      } else if (orderType === 'MTL') {
                        // MTL: Lấy giá mới nhất từ chart
                        const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                        if (lastCandle && lastCandle.close) {
                          price = parseFloat(lastCandle.close)
                        }
                      } else {
                        const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                        if (lastCandle && lastCandle.close) {
                          price = parseFloat(lastCandle.close)
                        }
                      }

                      if (price === 0) return 0
                      // Giá là nghìn VNĐ, balance là VNĐ
                      return Math.floor(availableBalance / (price * 1000))
                    } else {
                      // SELL - lấy từ positions
                      const existing = positions.find(p => p.symbol === symbol)
                      return existing ? existing.quantity : 0
                    }
                  }

                  const maxQuantity = calculateMaxQuantity()

                  return (
                    <>
                      <div className="order-action-buttons">
                        <button
                          className={`order-action-btn buy-btn ${orderSide === 'BUY' ? 'active' : ''}`}
                          onClick={() => {
                            setOrderSide('BUY')
                            handleSubmitOrder('BUY')
                          }}
                          disabled={orderSubmitting || !orderQuantity || parseInt(orderQuantity) === 0 || (orderType === 'LIMIT' && !orderPrice)}
                        >
                          MUA
                          <span className="order-value">Giá trị: {orderValue > 0 ? orderValue.toLocaleString('vi-VN') : '-'}</span>
                        </button>
                        <button
                          className={`order-action-btn sell-btn ${orderSide === 'SELL' ? 'active' : ''}`}
                          onClick={() => {
                            setOrderSide('SELL')
                            handleSubmitOrder('SELL')
                          }}
                          disabled={orderSubmitting || !orderQuantity || parseInt(orderQuantity) === 0 || (orderType === 'LIMIT' && !orderPrice)}
                        >
                          BÁN
                          <span className="order-value">Giá trị: {orderValue > 0 ? orderValue.toLocaleString('vi-VN') : '-'}</span>
                        </button>
                      </div>
                      <div className="max-quantity-info">
                        <span>Mua tối đa: {maxQuantity > 0 ? maxQuantity : 'q'}</span>
                        <span>Bán tối đa: {orderSide === 'SELL' ? maxQuantity : 0}</span>
                      </div>
                    </>
                  )
                })()}
              </>
            )}
          </div>

          {/* Positions */}
          {positions.length > 0 && (
            <div className="positions-section">
              <h3>Vị thế hiện tại</h3>
              <div className="positions-list">
                {positions.map(pos => (
                  <div key={pos.id} className="position-item">
                    <div className="position-header">
                      <span className="position-symbol">{pos.symbol}</span>
                      <span className={`position-pnl ${parseFloat(pos.unrealized_pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                        {parseFloat(pos.unrealized_pnl || 0) >= 0 ? '+' : ''}{parseFloat(pos.unrealized_pnl || 0).toLocaleString('vi-VN')} VNĐ
                      </span>
                    </div>
                    <div className="position-details">
                      <span>Số lượng: {pos.quantity}</span>
                      <span>Giá TB: {parseFloat(pos.avg_price || 0).toLocaleString('vi-VN')} VNĐ</span>
                      {pos.last_price && (
                        <span>Giá hiện tại: {parseFloat(pos.last_price).toLocaleString('vi-VN')} VNĐ</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Thử thách đầu tư */}
      <div className="challenge-section">
        <div className="challenge-section-header">
          <h3>Thử thách đầu tư</h3>
          <button
            className="rules-btn"
            onClick={() => setRulesModalOpen(true)}
            title="Xem luật chơi"
          >
            Luật chơi
          </button>
        </div>

        {/* Portfolio Info trong challenge - Hiển thị ở đầu khi challenge active */}
        {challengeActive && (
          <div className="portfolio-info challenge-portfolio challenge-portfolio-spacing">
            <h3>Số dư thử thách</h3>
            <div className="portfolio-items-row">
              <div className="portfolio-item">
                <span className="portfolio-label">Tiền mặt:</span>
                <span className="portfolio-value">{challengeBalance.toLocaleString('vi-VN')} VNĐ</span>
              </div>
              <div className="portfolio-item">
                <span className="portfolio-label">Tổng giá trị:</span>
                <span className={`portfolio-value ${challengeTotalValue >= challengeCapital ? 'positive' : 'negative'}`}>
                  {challengeTotalValue.toLocaleString('vi-VN')} VNĐ
                </span>
              </div>
              <div className="portfolio-item">
                <span className="portfolio-label">Lãi/Lỗ:</span>
                <span className={`portfolio-value ${challengeTotalValue >= challengeCapital ? 'positive' : 'negative'}`}>
                  {challengeTotalValue >= challengeCapital ? '+' : ''}{(challengeTotalValue - challengeCapital).toLocaleString('vi-VN')} VNĐ
                  ({((challengeTotalValue - challengeCapital) / challengeCapital * 100).toFixed(2)}%)
                </span>
              </div>
            </div>

            {/* Số lượng đã mua */}
            {challengePositions.length > 0 && (
              <div className="challenge-positions">
                <h4>Số lượng đã mua:</h4>
                <div className="challenge-positions-list">
                  {challengePositions.map(pos => (
                    <div key={pos.symbol} className="challenge-position-item">
                      <span className="position-symbol">{pos.symbol}:</span>
                      <span className="position-quantity">{pos.quantity} cổ phiếu</span>
                      {pos.avg_price && (
                        <span className="position-avg-price">(Giá TB: {parseFloat(pos.avg_price).toLocaleString('vi-VN')} VNĐ)</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!challengeActive ? (
          <div className="challenge-setup">
            <div className="challenge-form">
              <div className="challenge-form-item">
                <label htmlFor="challenge-start-date">Ngày bắt đầu:</label>
                <div className="datetime-input-group">
                  <input
                    id="challenge-start-date"
                    type="date"
                    value={challengeStartDate}
                    onChange={(e) => setChallengeStartDate(e.target.value)}
                    className="date-input"
                  />
                  <input
                    id="challenge-start-time"
                    type="time"
                    value={challengeStartTime}
                    onChange={(e) => setChallengeStartTime(e.target.value)}
                    className="time-input"
                  />
                </div>
              </div>
              <div className="challenge-form-item">
                <label htmlFor="challenge-duration">Thời gian giao dịch:</label>
                <select
                  id="challenge-duration"
                  value={challengeDuration}
                  onChange={(e) => setChallengeDuration(e.target.value)}
                  className="challenge-select"
                >
                  <option value="1">1 ngày</option>
                  <option value="7">7 ngày</option>
                  <option value="30">1 tháng</option>
                </select>
              </div>
              <div className="challenge-form-item">
                <label>Vốn được cấp:</label>
                <span className="challenge-capital">{challengeCapital.toLocaleString('vi-VN')} VNĐ</span>
              </div>
              <button
                onClick={handleStartChallenge}
                className="start-challenge-btn"
                disabled={!challengeStartDate}
              >
                Bắt đầu thử thách
              </button>
            </div>
          </div>
        ) : (
          <div className="challenge-active">
            <div className="challenge-info">
              <div className="challenge-info-item">
                <span className="challenge-label">Ngày bắt đầu:</span>
                <span className="challenge-value">{new Date(challengeStartDate).toLocaleDateString('vi-VN')}</span>
              </div>
              <div className="challenge-info-item">
                <span className="challenge-label">Ngày hiện tại:</span>
                <span className="challenge-value">{new Date(challengeCurrentDate).toLocaleDateString('vi-VN')}</span>
              </div>
              <div className="challenge-info-item">
                <span className="challenge-label">Ngày kết thúc:</span>
                <span className="challenge-value">{new Date(challengeEndDate).toLocaleDateString('vi-VN')}</span>
              </div>
              <div className="challenge-info-item">
                <span className="challenge-label">Vốn ban đầu:</span>
                <span className="challenge-value">{challengeCapital.toLocaleString('vi-VN')} VNĐ</span>
              </div>
              <button
                onClick={handleEndChallenge}
                className="end-challenge-btn"
              >
                Kết thúc thử thách
              </button>
            </div>
          </div>
        )}
      </div>

      {/* AI Coach Panel */}
      {aiCoachOpen && (
        <div className="ai-coach-panel">
          <AICoach symbol={symbol} onClose={() => setAiCoachOpen(false)} />
        </div>
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={modalTitle}
        type={modalType}
      >
        {modalMessage}
      </Modal>

      {/* Rules Modal */}
      <Modal
        isOpen={rulesModalOpen}
        onClose={() => setRulesModalOpen(false)}
        title="📖 Luật chơi - Thử thách đầu tư"
        type="info"
      >
        <div className="rules-content">
          <h4>1. Mục đích</h4>
          <p>Thử thách đầu tư là chế độ thực hành giúp bạn học cách giao dịch chứng khoán trong môi trường mô phỏng với dữ liệu lịch sử thực tế.</p>

          <h4>2. Cách chơi</h4>
          <ul>
            <li><strong>Chọn ngày bắt đầu:</strong> Bạn có thể chọn bất kỳ ngày nào trong quá khứ để bắt đầu thử thách (Hiện tại bộ dữ liệu hỗ trợ từ ngày 11-09-2023)</li>
            <li><strong>Chọn thời gian giao dịch:</strong> 1 ngày, 7 ngày, hoặc 1 tháng (chỉ tính các ngày giao dịch, bỏ qua thứ 7 và chủ nhật)</li>
            <li><strong>Vốn được cấp:</strong> 10.000.000 VNĐ (mười triệu đồng)</li>
            <li><strong>Đặt lệnh:</strong> Trong chế độ thử thách, tất cả các lệnh sẽ được khớp ngay lập tức tại giá hiện tại trên biểu đồ</li>
          </ul>

          <h4>3. Bước nhảy thời gian</h4>
          <ul>
            <li>Bạn có thể nhảy thời gian bằng các nút: <strong>+1p, +5p, +30p, +1h, +1d</strong></li>
            <li>Hệ thống sẽ tự động bỏ qua khoảng nghỉ trưa (11:30 - 13:00) và chuyển sang phiên chiều</li>
            <li>Khi đến cuối phiên chiều (14:45), bước nhảy tiếp theo sẽ chuyển sang ngày giao dịch tiếp theo (bỏ qua thứ 7 và chủ nhật)</li>
            <li>Sau khi nhảy, bạn không thể quay lại thời điểm trước đó</li>
          </ul>

          <h4>4. Kết thúc thử thách</h4>
          <ul>
            <li>Thử thách sẽ tự động kết thúc khi hết thời gian đã chọn</li>
            <li>Bạn có thể kết thúc sớm bằng nút "Kết thúc thử thách"</li>
            <li>Hệ thống sẽ tính toán lãi/lỗ dựa trên số dư tiền mặt và giá trị các vị thế tại thời điểm kết thúc</li>
          </ul>

          <h4>5. Lưu ý</h4>
          <ul>
            <li>Tất cả các lệnh trong chế độ thử thách đều được khớp ngay lập tức</li>
            <li>Giá khớp lệnh là giá hiện tại trên biểu đồ tại thời điểm đặt lệnh</li>
            <li>Khi mua nhiều lần cùng một mã, giá trung bình sẽ được tính tự động</li>
            <li>Thử thách chỉ tính các ngày giao dịch (thứ 2 - thứ 6), không tính thứ 7 và chủ nhật</li>
            <li>Chúc bạn may mắn!</li>
          </ul>
        </div>
      </Modal>

    </div>
  )
}

export default TradingPage

