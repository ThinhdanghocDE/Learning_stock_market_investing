import { useState, useEffect } from 'react'
import api from '../../utils/api'
import './AdminHomepagePage.css'

function AdminHomepagePage() {
    const [settings, setSettings] = useState({
        hero_headline: '',
        hero_subheadline: '',
        hero_cta_text: '',
        about_title: '',
        about_mission: '',
        about_description_1: '',
        about_description_2: '',
        stat_1_value: '',
        stat_1_label: '',
        stat_2_value: '',
        stat_2_label: '',
        stat_3_value: '',
        stat_3_label: '',
        hero_banners: [],
        about_image_url: ''
    })
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [message, setMessage] = useState(null)

    useEffect(() => {
        fetchSettings()
    }, [])

    const fetchSettings = async () => {
        try {
            const response = await api.get('/homepage')
            if (response.data) {
                setSettings(response.data)
            }
        } catch (error) {
            console.error('Failed to fetch settings:', error)
            setMessage({ type: 'error', text: 'Không thể tải cài đặt trang chủ' })
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (e) => {
        const { name, value } = e.target
        setSettings(prev => ({
            ...prev,
            [name]: value
        }))
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setSaving(true)
        setMessage(null)
        try {
            await api.put('/homepage/admin', settings)
            setMessage({ type: 'success', text: 'Cập nhật thành công!' })
        } catch (error) {
            console.error('Failed to update settings:', error)
            const errorMsg = error.response?.data?.detail
                ? (typeof error.response.data.detail === 'object' ? JSON.stringify(error.response.data.detail) : error.response.data.detail)
                : 'Cập nhật thất bại. Vui lòng thử lại.'
            setMessage({ type: 'error', text: errorMsg })
        } finally {
            setSaving(false)
        }
    }

    if (loading) return <div className="p-4">Đang tải...</div>

    return (
        <div className="admin-homepage-page">
            <h1 className="page-title">Quản lý Trang chủ</h1>
            <p className="page-description">Chỉnh sửa nội dung hiển thị trên trang chủ</p>

            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}

            <form onSubmit={handleSubmit} className="settings-form">
                {/* Hero Section - Left */}
                <section className="form-section">
                    <h2>Hero Section</h2>
                    <div className="form-group">
                        <label>Tiêu đề chính</label>
                        <input
                            type="text"
                            name="hero_headline"
                            value={settings.hero_headline}
                            onChange={handleChange}
                            placeholder="Nhập tiêu đề chính..."
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Tiêu đề phụ</label>
                        <textarea
                            name="hero_subheadline"
                            value={settings.hero_subheadline}
                            onChange={handleChange}
                            rows="3"
                            placeholder="Nhập mô tả ngắn..."
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>CTA Button Text</label>
                        <input
                            type="text"
                            name="hero_cta_text"
                            value={settings.hero_cta_text}
                            onChange={handleChange}
                            placeholder="Vào Dashboard"
                            required
                        />
                    </div>
                </section>

                {/* About Us Section - Right */}
                <section className="form-section">
                    <h2>About Us Section</h2>
                    <div className="form-group">
                        <label>Tiêu đề</label>
                        <input
                            type="text"
                            name="about_title"
                            value={settings.about_title}
                            onChange={handleChange}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Sứ mệnh (Mission)</label>
                        <input
                            type="text"
                            name="about_mission"
                            value={settings.about_mission}
                            onChange={handleChange}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>About Image URL</label>
                        <input
                            type="text"
                            name="about_image_url"
                            value={settings.about_image_url || ''}
                            onChange={handleChange}
                            placeholder="https://example.com/image.jpg"
                        />
                    </div>
                </section>

                {/* Banner Images - Full Width */}
                <section className="form-section full-width">
                    <h2>Banner Images</h2>
                    <div className="banner-list">
                        {settings.hero_banners && settings.hero_banners.map((url, index) => (
                            <div key={index} className="banner-item">
                                {url && <img src={url} alt={`Banner ${index + 1}`} className="banner-preview" />}
                                <input
                                    type="text"
                                    value={url}
                                    onChange={(e) => {
                                        const newBanners = [...settings.hero_banners]
                                        newBanners[index] = e.target.value
                                        setSettings(prev => ({ ...prev, hero_banners: newBanners }))
                                    }}
                                    placeholder="Nhập URL hình ảnh..."
                                />
                                <button
                                    type="button"
                                    className="btn-remove"
                                    onClick={() => {
                                        const newBanners = settings.hero_banners.filter((_, i) => i !== index)
                                        setSettings(prev => ({ ...prev, hero_banners: newBanners }))
                                    }}
                                >
                                    Xóa
                                </button>
                            </div>
                        ))}
                        <button
                            type="button"
                            className="btn-add"
                            onClick={() => setSettings(prev => ({
                                ...prev,
                                hero_banners: [...(prev.hero_banners || []), '']
                            }))}
                        >
                            + Thêm Banner
                        </button>
                    </div>
                </section>

                {/* Stats Section - Full Width */}
                <section className="form-section full-width">
                    <h2>Thống kê hiển thị</h2>
                    <div className="stats-grid">
                        <div className="stat-card">
                            <label>Stat 1</label>
                            <input
                                name="stat_1_value"
                                value={settings.stat_1_value}
                                onChange={handleChange}
                                placeholder="10M+"
                            />
                            <input
                                name="stat_1_label"
                                value={settings.stat_1_label}
                                onChange={handleChange}
                                placeholder="Tiền ảo để thực hành"
                            />
                        </div>
                        <div className="stat-card">
                            <label>Stat 2</label>
                            <input
                                name="stat_2_value"
                                value={settings.stat_2_value}
                                onChange={handleChange}
                                placeholder="1000+"
                            />
                            <input
                                name="stat_2_label"
                                value={settings.stat_2_label}
                                onChange={handleChange}
                                placeholder="Mã cổ phiếu VN"
                            />
                        </div>
                        <div className="stat-card">
                            <label>Stat 3</label>
                            <input
                                name="stat_3_value"
                                value={settings.stat_3_value}
                                onChange={handleChange}
                                placeholder="24/7"
                            />
                            <input
                                name="stat_3_label"
                                value={settings.stat_3_label}
                                onChange={handleChange}
                                placeholder="AI hỗ trợ"
                            />
                        </div>
                    </div>
                </section>

                {/* Descriptions - Full Width with two columns */}
                <section className="form-section full-width">
                    <h2>Mô tả About Us</h2>
                    <div className="form-row">
                        <div className="form-group">
                            <label>Mô tả 1 (Vấn đề)</label>
                            <textarea
                                name="about_description_1"
                                value={settings.about_description_1}
                                onChange={handleChange}
                                rows="4"
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label>Mô tả 2 (Giải pháp)</label>
                            <textarea
                                name="about_description_2"
                                value={settings.about_description_2}
                                onChange={handleChange}
                                rows="4"
                                required
                            />
                        </div>
                    </div>
                </section>

                <div className="form-actions">
                    <button type="submit" className="btn-save" disabled={saving}>
                        {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
                    </button>
                </div>
            </form>
        </div>
    )
}

export default AdminHomepagePage
