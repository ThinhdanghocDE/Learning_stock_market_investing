import { useState, useEffect } from 'react'
import api from '../../utils/api'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    LineElement
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import './AdminStatsPage.css'

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    LineElement
)

function AdminStatsPage() {
    const [stats, setStats] = useState(null)
    const [tradingStats, setTradingStats] = useState(null)
    const [leaderboard, setLeaderboard] = useState([])
    const [lessonStats, setLessonStats] = useState([])
    const [popularStocks, setPopularStocks] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetchAllStats()
    }, [])

    const fetchAllStats = async () => {
        try {
            const [statsRes, tradingRes, leaderboardRes, lessonsRes, stocksRes] = await Promise.all([
                api.get('/admin/stats'),
                api.get('/admin/stats/trading'),
                api.get('/admin/stats/leaderboard'),
                api.get('/admin/stats/lessons'),
                api.get('/admin/stats/popular-stocks')
            ])
            setStats(statsRes.data)
            setTradingStats(tradingRes.data)
            setLeaderboard(leaderboardRes.data)
            setLessonStats(lessonsRes.data)
            setPopularStocks(stocksRes.data)
        } catch (err) {
            console.error('Failed to fetch stats:', err)
            setError('Không thể tải dữ liệu thống kê')
        } finally {
            setLoading(false)
        }
    }

    const formatNumber = (num) => {
        if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B'
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
        return num?.toLocaleString() || '0'
    }

    const formatCurrency = (num) => {
        return new Intl.NumberFormat('vi-VN').format(num) + ' đ'
    }

    // Chart data for Popular Stocks
    const stocksChartData = {
        labels: popularStocks.slice(0, 5).map(s => s.symbol),
        datasets: [
            {
                label: 'Số lệnh mua',
                data: popularStocks.slice(0, 5).map(s => s.buy_orders),
                backgroundColor: 'rgba(16, 185, 129, 0.8)',
            },
            {
                label: 'Số lệnh bán',
                data: popularStocks.slice(0, 5).map(s => s.sell_orders),
                backgroundColor: 'rgba(239, 68, 68, 0.8)',
            }
        ]
    }

    // Chart data for Lesson Completions (Doughnut)
    const lessonChartData = {
        labels: lessonStats.slice(0, 5).map(l => l.title.substring(0, 15) + '...'),
        datasets: [{
            data: lessonStats.slice(0, 5).map(l => l.completions || 1),
            backgroundColor: [
                'rgba(59, 130, 246, 0.8)',
                'rgba(16, 185, 129, 0.8)',
                'rgba(249, 115, 22, 0.8)',
                'rgba(139, 92, 246, 0.8)',
                'rgba(236, 72, 153, 0.8)'
            ],
            borderWidth: 0
        }]
    }

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#475569', font: { size: 12 } }
            }
        },
        scales: {
            x: { ticks: { color: '#475569' }, grid: { display: false } },
            y: { ticks: { color: '#475569' }, grid: { color: '#e2e8f0' } }
        }
    }

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: { color: '#475569', font: { size: 11 }, boxWidth: 12 }
            }
        }
    }

    if (loading) return <div className="stats-loading">Đang tải thống kê...</div>
    if (error) return <div className="stats-error">{error}</div>

    return (
        <div className="admin-stats-page">
            <div className="stats-header">
                <h1>Thống kê hệ thống</h1>
                <p>Tổng quan về hoạt động của nền tảng</p>
            </div>

            {/* Overview Cards */}
            <div className="stats-cards">
                <div className="stat-card">
                    <div className="stat-value">{stats?.total_users || 0}</div>
                    <div className="stat-label">Tổng người dùng</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{tradingStats?.new_users_month || 0}</div>
                    <div className="stat-label">Người dùng mới tháng</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{formatNumber(tradingStats?.total_orders || 0)}</div>
                    <div className="stat-label">Tổng giao dịch</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{formatNumber(tradingStats?.total_trading_value || 0)}</div>
                    <div className="stat-label">Tổng giá trị GD</div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="stats-grid">
                <div className="stats-section">
                    <h2>Giao dịch theo mã CP</h2>
                    <div className="admin-chart-container">
                        {popularStocks.length > 0 ? (
                            <Bar data={stocksChartData} options={chartOptions} />
                        ) : (
                            <div className="no-data">Chưa có dữ liệu giao dịch</div>
                        )}
                    </div>
                </div>

                <div className="stats-section">
                    <h2>Hoàn thành bài học</h2>
                    <div className="admin-chart-container">
                        {lessonStats.length > 0 ? (
                            <Doughnut data={lessonChartData} options={doughnutOptions} />
                        ) : (
                            <div className="no-data">Chưa có dữ liệu bài học</div>
                        )}
                    </div>
                </div>
            </div>

            {/* Tables Row */}
            <div className="stats-grid">
                {/* Leaderboard */}
                <div className="stats-section">
                    <h2>Top Traders</h2>
                    <table className="stats-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Trader</th>
                                <th>Tài sản</th>
                                <th>Lợi nhuận</th>
                            </tr>
                        </thead>
                        <tbody>
                            {leaderboard.length > 0 ? leaderboard.map((trader) => (
                                <tr key={trader.user_id}>
                                    <td className="rank">{trader.rank}</td>
                                    <td className="username">{trader.username}</td>
                                    <td>{formatCurrency(trader.total_value)}</td>
                                    <td className={trader.profit >= 0 ? 'profit positive' : 'profit negative'}>
                                        {trader.profit >= 0 ? '+' : ''}{trader.profit_percent}%
                                    </td>
                                </tr>
                            )) : (
                                <tr><td colSpan="4" className="no-data">Chưa có dữ liệu</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Popular Stocks Table */}
                <div className="stats-section">
                    <h2>Cổ phiếu phổ biến</h2>
                    <table className="stats-table">
                        <thead>
                            <tr>
                                <th>Mã CP</th>
                                <th>Số lệnh</th>
                                <th>Khối lượng</th>
                                <th>Mua/Bán</th>
                            </tr>
                        </thead>
                        <tbody>
                            {popularStocks.length > 0 ? popularStocks.map((stock) => (
                                <tr key={stock.symbol}>
                                    <td className="symbol">{stock.symbol}</td>
                                    <td>{stock.total_orders}</td>
                                    <td>{formatNumber(stock.total_volume)}</td>
                                    <td>
                                        <span className="buy-count">{stock.buy_orders}</span>
                                        /
                                        <span className="sell-count">{stock.sell_orders}</span>
                                    </td>
                                </tr>
                            )) : (
                                <tr><td colSpan="4" className="no-data">Chưa có dữ liệu</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Lesson Stats - Full Width */}
            <div className="stats-section full-width">
                <h2>Thống kê bài học</h2>
                <table className="stats-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Tên bài học</th>
                            <th>Độ khó</th>
                            <th>Lượt học</th>
                            <th>Hoàn thành</th>
                            <th>Điểm TB</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lessonStats.length > 0 ? lessonStats.map((lesson) => (
                            <tr key={lesson.id}>
                                <td>{lesson.id}</td>
                                <td className="lesson-title">{lesson.title}</td>
                                <td>
                                    <span className={`difficulty ${lesson.difficulty_level}`}>
                                        {lesson.difficulty_level}
                                    </span>
                                </td>
                                <td>{lesson.total_attempts}</td>
                                <td>{lesson.completions}</td>
                                <td>{lesson.avg_quiz_score}%</td>
                            </tr>
                        )) : (
                            <tr><td colSpan="6" className="no-data">Chưa có dữ liệu</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default AdminStatsPage
