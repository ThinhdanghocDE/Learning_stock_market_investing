import { useState, useEffect, useRef, useCallback } from 'react'
import { createChart } from 'lightweight-charts'
import api from '../../utils/api'
import './ChartPractice.css'

function ChartPractice({ symbol: initialSymbol, startDate, durationDays = 7 }) {
    // Chart refs
    const chartContainerRef = useRef(null)
    const chartRef = useRef(null)
    const candlestickSeriesRef = useRef(null)
    const volumeSeriesRef = useRef(null)
    const historicalCandlesRef = useRef([])

    // State
    const [symbol, setSymbol] = useState(initialSymbol || 'ACB')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [currentDate, setCurrentDate] = useState(startDate)
    const [currentTime, setCurrentTime] = useState('09:00')
    const [endDate, setEndDate] = useState('')
    const [legendData, setLegendData] = useState({ open: '-', high: '-', low: '-', close: '-', volume: '-' })

    // Practice state
    const initialCapital = 10000000
    const [balance, setBalance] = useState(initialCapital) // 10 triệu VNĐ
    const [positions, setPositions] = useState([])
    const [totalValue, setTotalValue] = useState(initialCapital)
    const [orderQuantity, setOrderQuantity] = useState('')
    const [pnl, setPnl] = useState(0)
    const [pnlPercent, setPnlPercent] = useState(0)

    // Calculate end date
    useEffect(() => {
        if (startDate) {
            const start = new Date(startDate)
            const end = new Date(start)
            end.setDate(end.getDate() + durationDays)
            setEndDate(end.toISOString().split('T')[0])
            setCurrentDate(startDate)
            setCurrentTime('09:00')
        }
    }, [startDate, durationDays])

    // Initialize chart
    useEffect(() => {
        if (!chartContainerRef.current) return

        // Cleanup
        if (chartRef.current) {
            chartRef.current.remove()
            chartRef.current = null
        }

        const container = chartContainerRef.current

        const chart = createChart(container, {
            width: container.clientWidth,
            height: 450,
            layout: {
                background: { color: '#1e222d' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            rightPriceScale: {
                scaleMargins: { top: 0.1, bottom: 0.25 },
                borderColor: '#2a2e39',
            },
            timeScale: {
                borderColor: '#2a2e39',
                timeVisible: true,
                secondsVisible: false,
            },
            crosshair: {
                mode: 1,
                vertLine: {
                    color: '#758696',
                    width: 1,
                    style: 3,
                },
                horzLine: {
                    color: '#758696',
                    width: 1,
                    style: 3,
                },
            },
        })

        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        })

        const volumeSeries = chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        })

        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.85, bottom: 0 },
        })

        // Crosshair
        chart.subscribeCrosshairMove((param) => {
            if (!param.time || param.point.x < 0 || param.point.y < 0) {
                const lastCandle = historicalCandlesRef.current[historicalCandlesRef.current.length - 1]
                if (lastCandle) {
                    setLegendData({
                        open: lastCandle.open?.toFixed(2) || '-',
                        high: lastCandle.high?.toFixed(2) || '-',
                        low: lastCandle.low?.toFixed(2) || '-',
                        close: lastCandle.close?.toFixed(2) || '-',
                        volume: formatVolume(lastCandle.volume),
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
                    volume: formatVolume(volume?.value),
                })
            }
        })

        chartRef.current = chart
        candlestickSeriesRef.current = candlestickSeries
        volumeSeriesRef.current = volumeSeries

        // Handle resize
        const handleResize = () => {
            if (container && chartRef.current) {
                chartRef.current.applyOptions({
                    width: container.clientWidth,
                })
            }
        }

        window.addEventListener('resize', handleResize)

        return () => {
            window.removeEventListener('resize', handleResize)
            if (chartRef.current) {
                chartRef.current.remove()
                chartRef.current = null
            }
        }
    }, [])

    // Format volume
    const formatVolume = (vol) => {
        if (!vol) return '-'
        if (vol >= 1000000000) return (vol / 1000000000).toFixed(2) + 'B'
        if (vol >= 1000000) return (vol / 1000000).toFixed(2) + 'M'
        if (vol >= 1000) return (vol / 1000).toFixed(2) + 'K'
        return vol.toLocaleString()
    }

    // Fetch historical data
    const fetchData = useCallback(async () => {
        if (!symbol || !startDate || !currentDate) return

        setLoading(true)
        setError(null)

        try {
            // Calculate view start (7 days before start)
            const viewStart = new Date(startDate)
            viewStart.setDate(viewStart.getDate() - 7)
            const viewStartStr = viewStart.toISOString().split('T')[0]

            // End time based on current date/time
            const endDateTime = `${currentDate}T${currentTime}:00+07:00`
            const startDateTime = `${viewStartStr}T00:00:00+07:00`

            const response = await api.get(
                `/ohlc/historical?symbol=${symbol}&interval=1m&start_time=${encodeURIComponent(startDateTime)}&end_time=${encodeURIComponent(endDateTime)}&limit=10000`
            )

            if (response.data?.data) {
                const candles = response.data.data.map(candle => ({
                    time: Math.floor(new Date(candle.time).getTime() / 1000) + (7 * 60 * 60), // UTC+7
                    open: parseFloat(candle.open),
                    high: parseFloat(candle.high),
                    low: parseFloat(candle.low),
                    close: parseFloat(candle.close),
                    volume: parseInt(candle.volume || 0),
                }))

                // Sort and dedupe
                const sorted = candles.sort((a, b) => a.time - b.time)
                const deduped = sorted.filter((candle, index, arr) =>
                    index === 0 || candle.time !== arr[index - 1].time
                )

                historicalCandlesRef.current = deduped

                if (candlestickSeriesRef.current) {
                    candlestickSeriesRef.current.setData(deduped)
                }

                if (volumeSeriesRef.current) {
                    volumeSeriesRef.current.setData(deduped.map(c => ({
                        time: c.time,
                        value: c.volume,
                        color: c.close >= c.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
                    })))
                }

                // Update legend with last candle
                if (deduped.length > 0) {
                    const last = deduped[deduped.length - 1]
                    setLegendData({
                        open: last.open.toFixed(2),
                        high: last.high.toFixed(2),
                        low: last.low.toFixed(2),
                        close: last.close.toFixed(2),
                        volume: formatVolume(last.volume),
                    })

                    // Update total value
                    updateTotalValue(last.close)
                }
            }
        } catch (err) {
            console.error('Error fetching chart data:', err)
            setError('Không thể tải dữ liệu chart')
        } finally {
            setLoading(false)
        }
    }, [symbol, startDate, currentDate, currentTime])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    // Update total value based on positions
    const updateTotalValue = (currentPrice) => {
        let positionsValue = 0
        const position = positions.find(p => p.symbol === symbol)
        if (position) {
            positionsValue = currentPrice * position.quantity * 1000
            const profit = (currentPrice - position.avgPrice) * position.quantity * 1000
            const profitPercent = position.avgPrice > 0 ? ((currentPrice - position.avgPrice) / position.avgPrice * 100) : 0
            setPnl(profit)
            setPnlPercent(profitPercent)
        } else {
            setPnl(0)
            setPnlPercent(0)
        }
        setTotalValue(balance + positionsValue)
    }

    // Skip time
    const skipTime = (minutes) => {
        const [hours, mins] = currentTime.split(':').map(Number)
        let newMins = mins + minutes
        let newHours = hours
        let newDate = currentDate

        while (newMins >= 60) {
            newMins -= 60
            newHours += 1
        }

        // Check if past end of day (15:00)
        if (newHours >= 15) {
            // Move to next day
            const nextDay = new Date(currentDate)
            nextDay.setDate(nextDay.getDate() + 1)

            // Skip weekends
            while (nextDay.getDay() === 0 || nextDay.getDay() === 6) {
                nextDay.setDate(nextDay.getDate() + 1)
            }

            newDate = nextDay.toISOString().split('T')[0]
            newHours = 9
            newMins = 0
        }

        // Check if past end date
        if (newDate > endDate) {
            return // Don't go past end
        }

        setCurrentTime(`${String(newHours).padStart(2, '0')}:${String(newMins).padStart(2, '0')}`)
        setCurrentDate(newDate)
    }

    const skipDay = () => {
        const nextDay = new Date(currentDate)
        nextDay.setDate(nextDay.getDate() + 1)

        // Skip weekends
        while (nextDay.getDay() === 0 || nextDay.getDay() === 6) {
            nextDay.setDate(nextDay.getDate() + 1)
        }

        const newDate = nextDay.toISOString().split('T')[0]

        if (newDate > endDate) return

        setCurrentDate(newDate)
        setCurrentTime('09:00')
    }

    // Get current price
    const getCurrentPrice = () => {
        const candles = historicalCandlesRef.current
        if (candles.length === 0) return 0
        return candles[candles.length - 1].close
    }

    // Adjust quantity
    const adjustQuantity = (delta) => {
        const current = parseInt(orderQuantity) || 0
        const newQty = Math.max(0, current + delta)
        setOrderQuantity(newQty > 0 ? String(newQty) : '')
    }

    // Buy
    const handleBuy = () => {
        const quantity = parseInt(orderQuantity)
        if (!quantity || quantity <= 0) return

        const currentPrice = getCurrentPrice()
        if (currentPrice <= 0) return

        const cost = currentPrice * quantity * 1000

        if (cost > balance) {
            alert('Không đủ số dư')
            return
        }

        setBalance(prev => prev - cost)
        setPositions(prev => {
            const existing = prev.find(p => p.symbol === symbol)
            if (existing) {
                const newAvgPrice = (existing.avgPrice * existing.quantity + currentPrice * quantity) / (existing.quantity + quantity)
                return prev.map(p =>
                    p.symbol === symbol
                        ? { ...p, quantity: p.quantity + quantity, avgPrice: newAvgPrice }
                        : p
                )
            }
            return [...prev, { symbol, quantity, avgPrice: currentPrice }]
        })

        setOrderQuantity('')
    }

    // Sell
    const handleSell = () => {
        const quantity = parseInt(orderQuantity)
        if (!quantity || quantity <= 0) return

        const currentPrice = getCurrentPrice()
        if (currentPrice <= 0) return

        const existing = positions.find(p => p.symbol === symbol)
        if (!existing || existing.quantity < quantity) {
            alert('Không đủ số lượng để bán')
            return
        }

        const proceeds = currentPrice * quantity * 1000

        setBalance(prev => prev + proceeds)
        setPositions(prev => {
            return prev.map(p => {
                if (p.symbol === symbol) {
                    const newQty = p.quantity - quantity
                    if (newQty <= 0) {
                        return null
                    }
                    return { ...p, quantity: newQty }
                }
                return p
            }).filter(Boolean)
        })

        setOrderQuantity('')
    }

    // Reset
    const handleReset = () => {
        setBalance(initialCapital)
        setPositions([])
        setTotalValue(initialCapital)
        setPnl(0)
        setPnlPercent(0)
        setCurrentDate(startDate)
        setCurrentTime('09:00')
        setOrderQuantity('')
    }

    const position = positions.find(p => p.symbol === symbol)
    const currentPrice = getCurrentPrice()

    return (
        <div className="chart-practice-container">
            {/* Chart Section */}
            <div className="chart-section">
                <div className="chart-legend">
                    <span className="symbol-tag">{symbol}</span>
                    <span className="ohlc-item">O: <b>{legendData.open}</b></span>
                    <span className="ohlc-item">H: <b className="high">{legendData.high}</b></span>
                    <span className="ohlc-item">L: <b className="low">{legendData.low}</b></span>
                    <span className="ohlc-item">C: <b>{legendData.close}</b></span>
                    <span className="ohlc-item">V: <b>{legendData.volume}</b></span>
                </div>

                <div className="chart-wrapper" ref={chartContainerRef}>
                    {loading && <div className="chart-overlay">Đang tải...</div>}
                    {error && <div className="chart-overlay error">{error}</div>}
                </div>

                <div className="chart-footer">
                    <span className="current-time">{currentDate} {currentTime}</span>
                    <span className="time-range">{startDate} → {endDate}</span>
                </div>
            </div>

            {/* Trading Panel */}
            <div className="trading-panel">
                <div className="panel-header">
                    <span className="symbol-display">{symbol}</span>
                    <button className="btn-reset" onClick={handleReset} title="Reset">×</button>
                </div>

                <div className="panel-section">
                    <div className="info-row">
                        <span className="label">Sức mua:</span>
                        <span className="value">{balance.toLocaleString('vi-VN')} VNĐ</span>
                    </div>
                    {position && (
                        <div className="position-info">
                            <div className="info-row">
                                <span className="label">Đang giữ:</span>
                                <span className="value">{position.quantity} CP</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Giá TB:</span>
                                <span className="value">{(position.avgPrice * 1000).toLocaleString('vi-VN')}</span>
                            </div>
                            <div className="info-row">
                                <span className="label">Lãi/Lỗ:</span>
                                <span className={`value ${pnl >= 0 ? 'profit' : 'loss'}`}>
                                    {pnl >= 0 ? '+' : ''}{pnl.toLocaleString('vi-VN')} ({pnlPercent.toFixed(2)}%)
                                </span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="panel-section order-section">
                    <div className="order-label">KL đặt</div>
                    <div className="quantity-input-group">
                        <input
                            type="number"
                            placeholder="Nhập số lượng"
                            value={orderQuantity}
                            onChange={(e) => setOrderQuantity(e.target.value)}
                            min="1"
                            step="100"
                        />
                        <button className="btn-adjust" onClick={() => adjustQuantity(100)}>+</button>
                    </div>

                    <div className="order-buttons">
                        <button className="btn-buy" onClick={handleBuy}>MUA</button>
                        <button className="btn-sell" onClick={handleSell} disabled={!position}>BÁN</button>
                    </div>
                </div>

                <div className="panel-section skip-section">
                    <div className="skip-label">Bước nhảy thời gian:</div>
                    <div className="skip-buttons">
                        <button onClick={() => skipTime(1)}>+1p</button>
                        <button onClick={() => skipTime(5)}>+5p</button>
                        <button onClick={() => skipTime(30)}>+30p</button>
                        <button onClick={() => skipTime(60)}>+1h</button>
                        <button onClick={() => skipDay()}>+1d</button>
                    </div>
                </div>

                <div className="panel-section summary-section">
                    <div className="info-row total">
                        <span className="label">Tổng tài sản:</span>
                        <span className={`value ${totalValue >= initialCapital ? 'profit' : 'loss'}`}>
                            {totalValue.toLocaleString('vi-VN')} VNĐ
                        </span>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ChartPractice
