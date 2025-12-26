import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from '../../utils/api'
import './AdminLayout.css'

function AdminLayout() {
    const navigate = useNavigate()
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const checkAdmin = async () => {
            try {
                const response = await api.get('/auth/me')
                if (response.data.role !== 'ADMIN') {
                    // Không phải admin, chuyển về dashboard
                    navigate('/dashboard')
                    return
                }
                setUser(response.data)
            } catch (error) {
                console.error('Auth error:', error)
                navigate('/login')
            } finally {
                setLoading(false)
            }
        }
        checkAdmin()
    }, [navigate])

    if (loading) {
        return <div className="admin-loading">Đang kiểm tra quyền truy cập...</div>
    }

    return (
        <div className="admin-layout">
            {/* Sidebar */}
            <aside className="admin-sidebar">
                <div className="sidebar-header">
                    <h2>Admin Panel</h2>
                </div>
                <nav className="sidebar-nav">
                    <NavLink to="/admin/homepage" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
                        Trang chủ
                    </NavLink>
                    <NavLink to="/admin/lessons" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
                        Bài học
                    </NavLink>
                    <NavLink to="/admin/users" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
                        Người dùng
                    </NavLink>
                    <NavLink to="/admin/stats" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
                        Thống kê
                    </NavLink>
                </nav>
                <div className="sidebar-footer">
                    <NavLink to="/dashboard" className="nav-item back-link">
                        ← Về trang chính
                    </NavLink>
                </div>
            </aside>

            {/* Main Content */}
            <main className="admin-main">
                <Outlet />
            </main>
        </div>
    )
}

export default AdminLayout
