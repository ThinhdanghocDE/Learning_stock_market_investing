import { useState, useEffect } from 'react'
import api from '../../utils/api'
import './Admin.css'

function AdminUsersPage() {
    const [users, setUsers] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetchUsers()
    }, [])

    const fetchUsers = async () => {
        try {
            const response = await api.get('/admin/users')
            setUsers(response.data)
        } catch (err) {
            setError('Không thể tải danh sách người dùng')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const handleRoleChange = async (userId, newRole) => {
        if (!window.confirm(`Bạn có chắc muốn đổi role thành ${newRole}?`)) return

        try {
            await api.put(`/admin/users/${userId}/role?role=${newRole}`)
            // Cập nhật lại danh sách
            setUsers(users.map(u =>
                u.id === userId ? { ...u, role: newRole } : u
            ))
        } catch (err) {
            alert(err.response?.data?.detail || 'Không thể cập nhật role')
            console.error(err)
        }
    }

    if (loading) return <div className="admin-loading">Đang tải...</div>

    return (
        <div className="admin-page">
            <div className="admin-header">
                <h1>Quản lý Người dùng</h1>
            </div>

            {error && <div className="admin-error">{error}</div>}

            <div className="admin-table-container">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Điểm kinh nghiệm</th>
                            <th>Ngày tạo</th>
                            <th>Lần đăng nhập cuối</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((user) => (
                            <tr key={user.id}>
                                <td>{user.id}</td>
                                <td>{user.username}</td>
                                <td>{user.email || '-'}</td>
                                <td>
                                    <select
                                        value={user.role}
                                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                                        className={`role-select ${user.role?.toLowerCase()}`}
                                    >
                                        <option value="USER">USER</option>
                                        <option value="ADMIN">ADMIN</option>
                                    </select>
                                </td>
                                <td>{user.experience_points?.toLocaleString()}</td>
                                <td>{user.created_at ? new Date(user.created_at).toLocaleDateString('vi-VN') : '-'}</td>
                                <td>{user.last_login ? new Date(user.last_login).toLocaleDateString('vi-VN') : 'Chưa đăng nhập'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default AdminUsersPage
