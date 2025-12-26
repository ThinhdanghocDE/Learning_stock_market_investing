import { Outlet, Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuthStore } from '../../stores/authStore'
import api from '../../utils/api'
import './Layout.css'

function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const navItems = [
    // { path: '/dashboard', label: 'Dashboard' }, // Tạm ẩn
    { path: '/trading', label: 'Giao Dịch' },
    { path: '/learning', label: 'Học Tập' },
    { path: '/portfolio', label: 'Danh Mục' },
    { path: '/exchange', label: 'Đổi Sao' },
  ]

  // Thêm menu Admin nếu user là ADMIN
  if (user?.role === 'ADMIN') {
    navItems.push({ path: '/admin/lessons', label: 'Admin' })
  }

  const [portfolio, setPortfolio] = useState(null)

  // Fetch portfolio để hiển thị số dư
  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await api.get('/portfolio/summary')
        if (response.data && response.data.portfolio) {
          setPortfolio(response.data.portfolio)
        } else if (response.data) {
          // Fallback: nếu response.data là portfolio trực tiếp
          setPortfolio(response.data)
        }
      } catch (error) {
        console.error('Error fetching portfolio in Layout:', error)
        // Không set portfolio nếu lỗi, để tránh crash
      }
    }

    fetchPortfolio()
    // Auto-refresh mỗi 5 giây
    const interval = setInterval(fetchPortfolio, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          <h1 className="logo">Mindvest Learn</h1>
          <nav className="nav">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-link ${location.pathname.startsWith(item.path) ? 'active' : ''}`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="user-menu">
            {portfolio && (
              <div className="balance-info">
                <span className="balance-item">
                  <span className="balance-label">Số dư:</span>
                  <span className="balance-value">{parseFloat(portfolio.cash_balance || 0).toLocaleString('vi-VN')}</span>
                </span>
                <span className="balance-item">
                  <span className="balance-label">Phong tỏa:</span>
                  <span className="balance-value blocked">{parseFloat(portfolio.blocked_cash || 0).toLocaleString('vi-VN')}</span>
                </span>
                <span className="balance-item">
                  <span className="balance-label">Khả dụng:</span>
                  <span className="balance-value available">{parseFloat((portfolio.cash_balance || 0) - (portfolio.blocked_cash || 0)).toLocaleString('vi-VN')}</span>
                </span>
              </div>
            )}
            <div className="user-info">
              <span className="username">{user?.username}</span>
              <span className="points">⭐ {user?.experience_points || 0}</span>
            </div>
            <button onClick={logout} className="logout-btn">
              Đăng xuất
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout

