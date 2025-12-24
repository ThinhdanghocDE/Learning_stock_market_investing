import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../utils/api'
import './Learning.css'

function LearningPage() {
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchLessons = async () => {
      try {
        const response = await api.get('/lessons')
        setLessons(response.data)
      } catch (error) {
        console.error('Error fetching lessons:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchLessons()
  }, [])

  if (loading) {
    return <div className="loading">Đang tải...</div>
  }

  return (
    <div className="learning-page">
      <h1 className="page-title">Học Tập</h1>
      <p className="page-subtitle">Chọn bài học để bắt đầu</p>

      <div className="lessons-grid">
        {lessons.map((lesson) => (
          <Link
            key={lesson.id}
            to={`/learning/${lesson.id}`}
            className="lesson-card"
          >
            <div className="lesson-header">
              <h3>{lesson.title}</h3>
              <span className={`difficulty-badge ${lesson.difficulty_level?.toLowerCase()}`}>
                {lesson.difficulty_level}
              </span>
            </div>
            <p className="lesson-description">{lesson.description}</p>
            <div className="lesson-footer">
              <span className="lesson-duration">{lesson.estimated_duration || 'N/A'} phút</span>
              {lesson.chart_start_time && (
                <span className="lesson-chart">Có biểu đồ</span>
              )}
            </div>
          </Link>
        ))}
      </div>

      {lessons.length === 0 && (
        <div className="empty-state">
          <p>Chưa có bài học nào. Vui lòng thêm bài học từ admin.</p>
        </div>
      )}
    </div>
  )
}

export default LearningPage

