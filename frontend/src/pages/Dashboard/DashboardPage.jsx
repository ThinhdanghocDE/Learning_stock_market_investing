import { useEffect, useState } from 'react'
import { useAuthStore } from '../../stores/authStore'
import api from '../../utils/api'
import './Dashboard.css'

function DashboardPage() {
  const { user } = useAuthStore()
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await api.get('/portfolio/summary')
        // response.data có thể là {portfolio, positions, ...} hoặc portfolio trực tiếp
        if (response.data && response.data.portfolio) {
          setPortfolio(response.data.portfolio)
        } else if (response.data) {
          setPortfolio(response.data)
        }
      } catch (error) {
        console.error('Error fetching portfolio:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPortfolio()
  }, [])

  if (loading) {
    return <div className="loading">Đang tải...</div>
  }

  return (
    <div className="dashboard">
      <h1 className="page-title">Dashboard</h1>
      
      <div className="welcome-section">
        <h2>Chào mừng, {user?.username}!</h2>
        <p>Điểm kinh nghiệm: ⭐ {user?.experience_points || 0}</p>
      </div>

      {portfolio && (
        <div className="portfolio-summary">
          <div className="summary-card">
            <h3>Tổng giá trị</h3>
            <p className="value">{portfolio.total_value?.toLocaleString('vi-VN')} VNĐ</p>
          </div>
          <div className="summary-card">
            <h3>Tiền mặt</h3>
            <p className="value">{portfolio.cash_balance?.toLocaleString('vi-VN')} VNĐ</p>
          </div>
          <div className="summary-card">
            <h3>Giá trị danh mục</h3>
            <p className="value">{portfolio.total_positions_value?.toLocaleString('vi-VN')} VNĐ</p>
          </div>
          <div className="summary-card">
            <h3>Lãi/Lỗ</h3>
            <p className={`value ${portfolio.total_unrealized_pnl >= 0 ? 'profit' : 'loss'}`}>
              {portfolio.total_unrealized_pnl >= 0 ? '+' : ''}
              {portfolio.total_unrealized_pnl?.toLocaleString('vi-VN')} VNĐ
            </p>
          </div>
        </div>
      )}

      <div className="quick-actions">
        <h2>Thao tác nhanh</h2>
        <div className="action-buttons">
          <a href="/trading" className="action-btn">
            Bắt đầu giao dịch
          </a>
          <a href="/learning" className="action-btn">
            Học bài mới
          </a>
          <a href="/portfolio" className="action-btn">
            Xem danh mục
          </a>
        </div>
      </div>
    </div>
  )
}

export default DashboardPage

