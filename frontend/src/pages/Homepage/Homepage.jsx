import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import api from '../../utils/api'
import { Swiper, SwiperSlide } from 'swiper/react'
import { Navigation, Pagination, Autoplay } from 'swiper/modules'
import 'swiper/css'
import 'swiper/css/navigation'
import 'swiper/css/pagination'
import './Homepage.css'

function Homepage() {
    const { isAuthenticated } = useAuthStore()
    const [settings, setSettings] = useState({
        hero_headline: "Học đầu tư thông minh<br />cùng AI Mentor",
        hero_subheadline: "Thực hành giao dịch với tiền ảo, dữ liệu thật. AI phân tích mỗi quyết định và hướng dẫn bạn trở thành nhà đầu tư bài bản.",
        hero_cta_text: "Vào Dashboard",
        hero_banners: [],
        about_title: "Về Mindvest Learn",
        about_mission: "Sứ mệnh của chúng tôi là dân chủ hóa kiến thức đầu tư",
        about_description_1: "Chúng tôi nhận thấy rào cản lớn nhất của người mới bắt đầu đầu tư chứng khoán không phải là thiếu vốn, mà là thiếu kiến thức và kinh nghiệm thực chiến.",
        about_description_2: "Mindvest Learn được xây dựng để giải quyết vấn đề đó. Chúng tôi cung cấp môi trường giả lập an toàn, dữ liệu thực tế và đặc biệt là sự đồng hành của AI.",
        about_image_url: "",
        stat_1_value: "10M+",
        stat_1_label: "Tiền ảo để thực hành",
        stat_2_value: "1000+",
        stat_2_label: "Mã cổ phiếu VN",
        stat_3_value: "24/7",
        stat_3_label: "AI hỗ trợ"
    })
    const [showSuccessPopup, setShowSuccessPopup] = useState(false)

    const handleContactSubmit = (e) => {
        e.preventDefault()
        setShowSuccessPopup(true)
        e.target.reset()
        setTimeout(() => setShowSuccessPopup(false), 3000)
    }

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const response = await api.get('/homepage')
                if (response.data) {
                    setSettings(response.data)
                }
            } catch (error) {
                console.error('Failed to fetch homepage settings:', error)
            }
        }
        fetchSettings()
    }, [])

    return (
        <div className="homepage">
            {/* Success Popup */}
            {showSuccessPopup && (
                <div className="success-popup-overlay">
                    <div className="success-popup">
                        <div className="success-icon">✓</div>
                        <h3>Gửi yêu cầu thành công!</h3>
                        <p>Chúng tôi sẽ liên hệ với bạn trong 24h.</p>
                    </div>
                </div>
            )}

            {/* Homepage Header */}
            <header className="homepage-header">
                <div className="header-container">
                    <div className="logo">Mindvest Learn</div>
                    <nav className="header-nav">
                        {isAuthenticated && (
                            <Link to="/dashboard" className="nav-btn">Vào Dashboard</Link>
                        )}
                    </nav>
                </div>
            </header>

            {/* Hero Section */}
            <section className="hero-section">
                <div className="hero-content">
                    <h1 className="hero-headline" dangerouslySetInnerHTML={{ __html: settings.hero_headline.replace(/\n/g, '<br />') }}>
                    </h1>
                    <p className="hero-subheadline">
                        {settings.hero_subheadline}
                    </p>
                    <div className="hero-cta">
                        {isAuthenticated ? (
                            <Link to="/dashboard" className="btn-primary">
                                {settings.hero_cta_text}
                            </Link>
                        ) : (
                            <>
                                <Link to="/register" className="btn-primary">
                                    Bắt đầu miễn phí
                                </Link>
                                <Link to="/login" className="btn-secondary">
                                    Đăng nhập
                                </Link>
                            </>
                        )}
                    </div>
                    <div className="hero-stats">
                        <div className="stat-item">
                            <span className="stat-value">{settings.stat_1_value}</span>
                            <span className="stat-label">{settings.stat_1_label}</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">{settings.stat_2_value}</span>
                            <span className="stat-label">{settings.stat_2_label}</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">{settings.stat_3_value}</span>
                            <span className="stat-label">{settings.stat_3_label}</span>
                        </div>
                    </div>
                </div>
                <div className="hero-visual">
                    {settings.hero_banners && settings.hero_banners.length > 0 ? (
                        <Swiper
                            modules={[Navigation, Pagination, Autoplay]}
                            spaceBetween={20}
                            slidesPerView={1}
                            navigation
                            pagination={{ clickable: true }}
                            autoplay={{ delay: 5000 }}
                            className="hero-swiper"
                        >
                            {settings.hero_banners.map((url, index) => (
                                <SwiperSlide key={index}>
                                    <div className="banner-slide">
                                        <img src={url} alt={`Banner ${index + 1}`} />
                                    </div>
                                </SwiperSlide>
                            ))}
                        </Swiper>
                    ) : (
                        <div className="hero-image-container">
                            <img src="/images/hero_trading.png" alt="Stock Trading Dashboard" className="hero-image" />
                        </div>
                    )}
                </div>
            </section>

            {/* AI Section */}
            <section className="ai-section">
                <div className="section-header">
                    <span className="section-badge">AI-Powered</span>
                    <h2>AI Mentor cá nhân</h2>
                    <p>Không chỉ là công cụ, mà là người hướng dẫn thông minh đồng hành cùng bạn</p>
                </div>
                <div className="ai-features">
                    <div className="feature-card">
                        <div className="feature-number">01</div>
                        <h3>Phân tích cổ phiếu</h3>
                        <p>AI đọc hiểu biểu đồ, chỉ số tài chính và đưa ra nhận định khách quan về từng mã cổ phiếu bạn quan tâm.</p>
                    </div>
                    <div className="feature-card">
                        <div className="feature-number">02</div>
                        <h3>Nhận xét giao dịch</h3>
                        <p>Mỗi lệnh mua/bán bạn đặt, AI sẽ phân tích và cho bạn biết quyết định đó hợp lý hay cần cân nhắc lại.</p>
                    </div>
                    <div className="feature-card">
                        <div className="feature-number">03</div>
                        <h3>Tránh FOMO</h3>
                        <p>AI giúp bạn nhận ra khi nào đang bị cảm xúc chi phối, từ đó đưa ra quyết định đầu tư lý trí hơn.</p>
                    </div>
                </div>
            </section>

            {/* Trading Section */}
            <section className="trading-section">
                <div className="trading-content">
                    <div className="trading-text">
                        <span className="section-badge">Paper Trading</span>
                        <h2>Thực hành không lo mất tiền</h2>
                        <p className="trading-desc">
                            Sử dụng 10 triệu tiền ảo để giao dịch với dữ liệu giá cổ phiếu thật
                            từ thị trường Việt Nam. Học từ thực tế, không phải lý thuyết suông.
                        </p>
                        <ul className="trading-features">
                            <li>
                                <span className="check">✓</span>
                                Dữ liệu giá real-time từ HOSE, HNX
                            </li>
                            <li>
                                <span className="check">✓</span>
                                Đặt lệnh mua/bán như thật
                            </li>
                            <li>
                                <span className="check">✓</span>
                                Theo dõi danh mục đầu tư
                            </li>
                            <li>
                                <span className="check">✓</span>
                                Thử thách đầu tư với dữ liệu lịch sử
                            </li>
                        </ul>
                    </div>
                    <div className="trading-visual">
                        <div className="portfolio-preview">
                            <div className="portfolio-header">Danh mục của bạn</div>
                            <div className="portfolio-item">
                                <span className="stock">VNM</span>
                                <span className="shares">100 cp</span>
                                <span className="pnl up">+850,000</span>
                            </div>
                            <div className="portfolio-item">
                                <span className="stock">FPT</span>
                                <span className="shares">50 cp</span>
                                <span className="pnl up">+1,250,000</span>
                            </div>
                            <div className="portfolio-item">
                                <span className="stock">MWG</span>
                                <span className="shares">200 cp</span>
                                <span className="pnl down">-320,000</span>
                            </div>
                            <div className="portfolio-total">
                                <span>Tổng lãi/lỗ</span>
                                <span className="total-value up">+1,780,000</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Learning Section */}
            <section className="learning-section">
                <div className="section-header">
                    <span className="section-badge">Learning Path</span>
                    <h2>Học từ sai lầm, không phải từ tiền thật</h2>
                    <p>Mỗi giao dịch là một bài học. AI giúp bạn rút kinh nghiệm và tiến bộ mỗi ngày.</p>
                </div>
                <div className="learning-cards">
                    <div className="learning-card">
                        <div className="lesson-number">01</div>
                        <h4>Nhật ký giao dịch</h4>
                        <p>Lưu lại mọi quyết định và kết quả để bạn nhìn lại và học hỏi.</p>
                    </div>
                    <div className="learning-card">
                        <div className="lesson-number">02</div>
                        <h4>Phân tích lỗi</h4>
                        <p>AI chỉ ra những sai lầm phổ biến bạn hay mắc phải và cách khắc phục.</p>
                    </div>
                    <div className="learning-card">
                        <div className="lesson-number">03</div>
                        <h4>Quản lý rủi ro</h4>
                        <p>Học cách đặt stop-loss, phân bổ vốn và bảo vệ danh mục đầu tư.</p>
                    </div>
                </div>
            </section>

            {/* About Us Section */}
            <section className="about-section">
                <div className="about-content">
                    <div className="section-header">
                        <h2>{settings.about_title}</h2>
                        <p>{settings.about_mission}</p>
                    </div>
                    <div className="about-grid">
                        <div className="about-text">
                            <h3>Tại sao Mindvest Learn ra đời?</h3>
                            <p>
                                {settings.about_description_1}
                            </p>
                            <p>
                                {settings.about_description_2}
                            </p>
                        </div>
                        <div className="about-stats">
                            {settings.about_image_url ? (
                                <img src={settings.about_image_url} alt="About Us" className="about-image" />
                            ) : (
                                <>
                                    <div className="stat-box">
                                        <span className="number">0đ</span>
                                        <span className="label">Rủi ro tài chính</span>
                                    </div>
                                    <div className="stat-box">
                                        <span className="number">100%</span>
                                        <span className="label">Dữ liệu thực tế</span>
                                    </div>
                                    <div className="stat-box">
                                        <span className="number">24/7</span>
                                        <span className="label">Học mọi lúc</span>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="cta-section">
                <div className="cta-content">
                    <h2>Sẵn sàng trở thành nhà đầu tư thông minh?</h2>
                    <p>Đăng ký ngay để nhận 10 triệu tiền ảo và bắt đầu hành trình đầu tư của bạn.</p>
                    {isAuthenticated ? (
                        <Link to="/trading" className="btn-cta">
                            Bắt đầu giao dịch
                        </Link>
                    ) : (
                        <Link to="/register" className="btn-cta">
                            Đăng ký miễn phí
                        </Link>
                    )}
                </div>
            </section>

            {/* Contact Section */}
            <section className="contact-section">
                <div className="contact-container">
                    <div className="contact-info">
                        <span className="section-badge">Liên hệ</span>
                        <h2>Hợp tác quảng cáo</h2>
                        <p>
                            Bạn muốn quảng bá sản phẩm/dịch vụ tài chính đến cộng đồng nhà đầu tư?
                            Hãy để lại thông tin, chúng tôi sẽ liên hệ trong 24h.
                        </p>
                        <div className="contact-details">
                            <div className="contact-item">
                                <span className="contact-label">Email</span>
                                <span className="contact-value">vuthinh122004@gmail.com</span>
                            </div>
                            <div className="contact-item">
                                <span className="contact-label">Hotline</span>
                                <span className="contact-value">0582676098</span>
                            </div>
                        </div>
                    </div>
                    <form className="contact-form" onSubmit={handleContactSubmit}>
                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="fullname">Họ và tên *</label>
                                <input type="text" id="fullname" />
                            </div>
                            <div className="form-group">
                                <label htmlFor="company">Công ty</label>
                                <input type="text" id="company" placeholder="Tên công ty" />
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label htmlFor="email">Email *</label>
                                <input type="email" id="email" />
                            </div>
                            <div className="form-group">
                                <label htmlFor="phone">Số điện thoại *</label>
                                <input type="tel" id="phone" />
                            </div>
                        </div>
                        <div className="form-group">
                            <label htmlFor="message">Nội dung *</label>
                            <textarea id="message" rows="4" placeholder="Mô tả nhu cầu quảng cáo của bạn..." required></textarea>
                        </div>
                        <button type="submit" className="btn-submit">Gửi yêu cầu</button>
                    </form>
                </div>
            </section>

            {/* Footer */}
            <footer className="homepage-footer">
                <p>© 2025 Mindvest Learn. Nền tảng thực hành đầu tư chứng khoán thông minh.</p>
            </footer>
        </div>
    )
}

export default Homepage
