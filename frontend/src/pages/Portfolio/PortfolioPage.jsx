import { useEffect, useState } from 'react'
import api from '../../utils/api'
import './Portfolio.css'

function PortfolioPage() {
  const [portfolio, setPortfolio] = useState(null)
  const [positions, setPositions] = useState([])
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [totalPositionsValue, setTotalPositionsValue] = useState(0)
  const [totalUnrealizedPnl, setTotalUnrealizedPnl] = useState(0)

  useEffect(() => {
    const fetchData = async () => {
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
        const [portfolioRes, positionsRes, ordersRes] = await Promise.all([
          api.get('/portfolio/summary'),
          api.get('/portfolio/positions'),
          api.get('/portfolio/orders?limit=50&trading_mode_filter=REALTIME'), // Chỉ lấy REALTIME orders
        ])

        // portfolioRes.data có thể là {portfolio, positions, ...} hoặc portfolio trực tiếp
        if (portfolioRes.data && portfolioRes.data.portfolio) {
          setPortfolio(portfolioRes.data.portfolio)
          setPositions(portfolioRes.data.positions || positionsRes.data || [])
          // Lấy total_positions_value và total_unrealized_pnl từ summary response
          setTotalPositionsValue(portfolioRes.data.total_positions_value || 0)
          setTotalUnrealizedPnl(portfolioRes.data.total_unrealized_pnl || 0)
        } else {
          setPortfolio(portfolioRes.data)
          setPositions(positionsRes.data || [])
          setTotalPositionsValue(0)
          setTotalUnrealizedPnl(0)
        }
        setOrders(ordersRes.data || [])
      } catch (error) {
        console.error('Error fetching portfolio data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // Auto-refresh mỗi 5 giây để cập nhật giá và fill QUEUED orders
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div className="loading">Đang tải...</div>
  }

  return (
    <div className="portfolio-page">
      <h1 className="page-title">Danh Mục Đầu Tư</h1>

      {portfolio && (
        <div className="portfolio-summary">
          <div className="summary-card">
            <h3>Tổng giá trị</h3>
            <p className="value">{portfolio.total_value ? parseFloat(portfolio.total_value).toLocaleString('vi-VN') : '0'} VNĐ</p>
          </div>
          <div className="summary-card">
            <h3>Tiền mặt</h3>
            <p className="value">{portfolio.cash_balance ? parseFloat(portfolio.cash_balance).toLocaleString('vi-VN') : '0'} VNĐ</p>
          </div>
          <div className="summary-card">
            <h3>Giá trị danh mục</h3>
            <p className="value">{totalPositionsValue ? parseFloat(totalPositionsValue).toLocaleString('vi-VN') : '0'} VNĐ</p>
          </div>
          <div className="summary-card">
            <h3>Lãi/Lỗ</h3>
            <p className={`value ${(totalUnrealizedPnl || 0) >= 0 ? 'profit' : 'loss'}`}>
              {(totalUnrealizedPnl || 0) >= 0 ? '+' : ''}
              {totalUnrealizedPnl ? parseFloat(totalUnrealizedPnl).toLocaleString('vi-VN') : '0'} VNĐ
            </p>
          </div>
        </div>
      )}

      <div className="positions-section">
        <h2>Vị thế</h2>
        {positions.length > 0 ? (
          <table className="positions-table">
            <thead>
              <tr>
                <th>Mã</th>
                <th>Số lượng</th>
                <th>Giá mua</th>
                <th>Giá hiện tại</th>
                <th>Lãi/Lỗ</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => {
                // Giá từ DB là nghìn VNĐ (ví dụ: 23.9 = 23,900 VNĐ), cần nhân 1000
                const avgPrice = position.average_price || position.avg_price
                const currentPrice = position.current_price || position.last_price
                const avgPriceVND = avgPrice ? parseFloat(avgPrice) * 1000 : 0
                const currentPriceVND = currentPrice ? parseFloat(currentPrice) * 1000 : 0
                
                return (
                  <tr key={position.id}>
                    <td>{position.symbol}</td>
                    <td>{position.quantity}</td>
                    <td>{avgPrice ? avgPriceVND.toLocaleString('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : 'N/A'} VNĐ</td>
                    <td>{currentPrice ? currentPriceVND.toLocaleString('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : 'N/A'} VNĐ</td>
                    <td className={(position.unrealized_pnl || 0) >= 0 ? 'profit' : 'loss'}>
                      {(position.unrealized_pnl || 0) >= 0 ? '+' : ''}
                      {position.unrealized_pnl ? parseFloat(position.unrealized_pnl).toLocaleString('vi-VN') : '0'} VNĐ
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <p className="empty-state">Chưa có vị thế nào</p>
        )}
      </div>

      <div className="orders-section">
        <h2>Lịch sử lệnh</h2>
        {orders.length > 0 ? (
          <table className="orders-table">
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Mã</th>
                <th>Loại</th>
                <th>Giá</th>
                <th>Số lượng</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td>{new Date(order.created_at).toLocaleString('vi-VN')}</td>
                  <td>{order.symbol}</td>
                  <td>{order.side} {order.order_type}</td>
                  <td>{order.filled_price || order.price || 'N/A'}</td>
                  <td>{order.filled_quantity || order.quantity}</td>
                  <td>
                    <span className={`status-badge ${order.status.toLowerCase()}`}>
                      {order.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty-state">Chưa có lệnh nào</p>
        )}
      </div>
    </div>
  )
}

export default PortfolioPage

