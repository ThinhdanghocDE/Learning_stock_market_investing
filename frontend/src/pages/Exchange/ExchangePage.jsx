import { useState, useEffect } from 'react'
import api from '../../utils/api'
import { useAuthStore } from '../../stores/authStore'
import './Exchange.css'

function ExchangePage() {
    const { user, checkAuth } = useAuthStore()
    const [stars, setStars] = useState('')
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState(null)
    const [portfolio, setPortfolio] = useState(null)
    const [history, setHistory] = useState([])
    const [activeTab, setActiveTab] = useState('exchange')

    const RATE = 10000 // 1 sao = 10,000 VND

    // Milestones rewards info
    const milestones = [
        { stars: 1000, reward: '10,000,000 VND', description: 'Hoàn thành 1 khóa học' },
        { stars: 5000, reward: '50,000,000 VND', description: 'Chinh phục cấp trung bình' },
        { stars: 10000, reward: '100,000,000 VND', description: 'Trở thành chuyên gia' },
    ]

    useEffect(() => {
        fetchPortfolio()
        fetchHistory()
    }, [])

    const fetchPortfolio = async () => {
        try {
            const response = await api.get('/portfolio/summary')
            setPortfolio(response.data.portfolio || response.data)
        } catch (error) {
            console.error('Error fetching portfolio:', error)
        }
    }

    const fetchHistory = async () => {
        // Mock history data - in real app, fetch from API
        setHistory([
            // { id: 1, stars: 500, money: 5000000, date: '2024-12-25' },
            // { id: 2, stars: 1000, money: 10000000, date: '2024-12-20' },
        ])
    }

    const handleExchange = async (e) => {
        e.preventDefault()
        const starsNum = parseInt(stars)

        if (!starsNum || starsNum <= 0) {
            setMessage({ type: 'error', text: 'Vui lòng nhập số sao hợp lệ' })
            return
        }

        if (starsNum > (user?.experience_points || 0)) {
            setMessage({ type: 'error', text: `Bạn chỉ có ${user?.experience_points || 0} sao` })
            return
        }

        setLoading(true)
        setMessage(null)

        try {
            const response = await api.post(`/auth/exchange-stars?stars=${starsNum}`)
            setMessage({ type: 'success', text: response.data.message })
            setStars('')
            await checkAuth()
            await fetchPortfolio()
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.response?.data?.detail || 'Quy đổi thất bại'
            })
        } finally {
            setLoading(false)
        }
    }

    const presetAmounts = [100, 500, 1000]
    const starsNum = parseInt(stars) || 0
    const moneyPreview = starsNum * RATE
    const currentStars = user?.experience_points || 0

    return (
        <div className="exchange-page">
            {/* Hero Section */}
            <div className="exchange-hero">
                <div className="hero-content">
                    <h1>Trung tâm quy đổi</h1>
                    <p>Biến kiến thức thành tài sản thực</p>
                </div>
                <div className="hero-stats">
                    <div className="hero-stat">
                        <span className="hero-stat-label">Sao hiện có</span>
                        <span className="hero-stat-value">{currentStars.toLocaleString()}</span>
                    </div>
                    <div className="hero-stat">
                        <span className="hero-stat-label">Số dư (VND)</span>
                        <span className="hero-stat-value">{parseFloat(portfolio?.cash_balance || 0).toLocaleString('vi-VN')}</span>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="exchange-main">
                {/* Left Column - Exchange Form */}
                <div className="exchange-form-section">
                    <div className="section-header">
                        <h2>Quy đổi ngay</h2>
                        <span className="rate-badge">1 sao = {RATE.toLocaleString()} VND</span>
                    </div>

                    <form onSubmit={handleExchange} className="exchange-form">
                        <div className="input-group">
                            <label>Số sao muốn đổi</label>
                            <input
                                type="number"
                                value={stars}
                                onChange={(e) => setStars(e.target.value)}
                                placeholder="Nhập số sao"
                                min="1"
                                max={currentStars}
                            />
                            <div className="input-hint">Tối đa: {currentStars.toLocaleString()} sao</div>
                        </div>

                        <div className="quick-amounts">
                            {presetAmounts.map(amount => (
                                <button
                                    key={amount}
                                    type="button"
                                    className={`amount-btn ${stars === amount.toString() ? 'active' : ''}`}
                                    onClick={() => setStars(amount.toString())}
                                    disabled={amount > currentStars}
                                >
                                    {amount.toLocaleString()}
                                </button>
                            ))}
                            <button
                                type="button"
                                className={`amount-btn max-btn ${stars === currentStars.toString() ? 'active' : ''}`}
                                onClick={() => setStars(currentStars.toString())}
                                disabled={!currentStars}
                            >
                                Tất cả
                            </button>
                        </div>

                        {starsNum > 0 && (
                            <div className="conversion-box">
                                <div className="conversion-item">
                                    <span className="conv-label">Đổi</span>
                                    <span className="conv-value from">{starsNum.toLocaleString()} sao</span>
                                </div>
                                <div className="conversion-arrow">→</div>
                                <div className="conversion-item">
                                    <span className="conv-label">Nhận</span>
                                    <span className="conv-value to">{moneyPreview.toLocaleString()} VND</span>
                                </div>
                            </div>
                        )}

                        {message && (
                            <div className={`form-message ${message.type}`}>
                                {message.text}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="submit-btn"
                            disabled={loading || !starsNum || starsNum > currentStars}
                        >
                            {loading ? 'Đang xử lý...' : 'Xác nhận quy đổi'}
                        </button>
                    </form>
                </div>

                {/* Right Column - Info */}
                <div className="exchange-info-section">
                    {/* How it works */}
                    <div className="info-card">
                        <h3>Cách thức hoạt động</h3>
                        <div className="steps">
                            <div className="step">
                                <div className="step-number">1</div>
                                <div className="step-content">
                                    <strong>Học và kiếm sao</strong>
                                    <p>Hoàn thành các bài học để nhận sao thưởng</p>
                                </div>
                            </div>
                            <div className="step">
                                <div className="step-number">2</div>
                                <div className="step-content">
                                    <strong>Quy đổi sao</strong>
                                    <p>Chuyển sao thành tiền mặt theo tỷ lệ cố định</p>
                                </div>
                            </div>
                            <div className="step">
                                <div className="step-number">3</div>
                                <div className="step-content">
                                    <strong>Giao dịch</strong>
                                    <p>Sử dụng tiền để thực hành giao dịch chứng khoán</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Milestones */}
                    <div className="info-card">
                        <h3>Mục tiêu phần thưởng</h3>
                        <div className="milestones">
                            {milestones.map((milestone, index) => (
                                <div
                                    key={index}
                                    className={`milestone ${currentStars >= milestone.stars ? 'achieved' : ''}`}
                                >
                                    <div className="milestone-progress">
                                        <div
                                            className="milestone-bar"
                                            style={{ width: `${Math.min(100, (currentStars / milestone.stars) * 100)}%` }}
                                        />
                                    </div>
                                    <div className="milestone-info">
                                        <span className="milestone-stars">{milestone.stars.toLocaleString()} sao</span>
                                        <span className="milestone-reward">{milestone.reward}</span>
                                    </div>
                                    <p className="milestone-desc">{milestone.description}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Tips */}
                    <div className="info-card tips-card">
                        <h3>Mẹo tích lũy sao</h3>
                        <ul className="tips-list">
                            <li>Hoàn thành quiz với điểm cao để nhận nhiều sao hơn</li>
                            <li>Học đều đặn mỗi ngày để duy trì streak</li>
                            <li>Thử thách bản thân với các bài học nâng cao</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ExchangePage
