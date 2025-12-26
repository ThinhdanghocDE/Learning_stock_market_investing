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

    const RATE = 10000 // 1 sao = 10,000 VND

    useEffect(() => {
        fetchPortfolio()
    }, [])

    const fetchPortfolio = async () => {
        try {
            const response = await api.get('/portfolio/summary')
            setPortfolio(response.data.portfolio || response.data)
        } catch (error) {
            console.error('Error fetching portfolio:', error)
        }
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
            // Refresh user data và portfolio
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

    const presetAmounts = [100, 500, 1000, 5000]
    const starsNum = parseInt(stars) || 0
    const moneyPreview = starsNum * RATE

    return (
        <div className="exchange-page">
            <div className="exchange-container">
                <div className="exchange-header">
                    <h1>⭐ Quy đổi Sao</h1>
                    <p>Đổi sao thành tiền mặt để giao dịch</p>
                </div>

                <div className="exchange-info">
                    <div className="info-card">
                        <span className="info-label">Số sao hiện có</span>
                        <span className="info-value stars">⭐ {user?.experience_points?.toLocaleString() || 0}</span>
                    </div>
                    <div className="info-card">
                        <span className="info-label">Số dư hiện tại</span>
                        <span className="info-value money">{parseFloat(portfolio?.cash_balance || 0).toLocaleString('vi-VN')} VND</span>
                    </div>
                    <div className="info-card rate">
                        <span className="info-label">Tỷ lệ quy đổi</span>
                        <span className="info-value">1 ⭐ = {RATE.toLocaleString()} VND</span>
                    </div>
                </div>

                <form onSubmit={handleExchange} className="exchange-form">
                    <div className="form-group">
                        <label>Số sao muốn đổi</label>
                        <input
                            type="number"
                            value={stars}
                            onChange={(e) => setStars(e.target.value)}
                            placeholder="Nhập số sao"
                            min="1"
                            max={user?.experience_points || 0}
                        />
                    </div>

                    <div className="preset-buttons">
                        {presetAmounts.map(amount => (
                            <button
                                key={amount}
                                type="button"
                                className="preset-btn"
                                onClick={() => setStars(amount.toString())}
                                disabled={amount > (user?.experience_points || 0)}
                            >
                                {amount.toLocaleString()} ⭐
                            </button>
                        ))}
                        <button
                            type="button"
                            className="preset-btn all"
                            onClick={() => setStars((user?.experience_points || 0).toString())}
                            disabled={!user?.experience_points}
                        >
                            Tất cả
                        </button>
                    </div>

                    {starsNum > 0 && (
                        <div className="preview">
                            <span>Bạn sẽ nhận được:</span>
                            <span className="preview-money">{moneyPreview.toLocaleString()} VND</span>
                        </div>
                    )}

                    {message && (
                        <div className={`message ${message.type}`}>
                            {message.text}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="exchange-btn"
                        disabled={loading || !starsNum || starsNum > (user?.experience_points || 0)}
                    >
                        {loading ? 'Đang xử lý...' : 'Quy đổi ngay'}
                    </button>
                </form>
            </div>
        </div>
    )
}

export default ExchangePage
