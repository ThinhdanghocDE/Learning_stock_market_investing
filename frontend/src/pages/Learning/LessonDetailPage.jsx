import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../../utils/api'
import './Learning.css'

function LessonDetailPage() {
  const { lessonId } = useParams()
  const [lesson, setLesson] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchLesson = async () => {
      try {
        const response = await api.get(`/lessons/${lessonId}`)
        setLesson(response.data)
      } catch (error) {
        console.error('Error fetching lesson:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchLesson()
  }, [lessonId])

  if (loading) {
    return <div className="loading">Đang tải...</div>
  }

  if (!lesson) {
    return <div className="error">Không tìm thấy bài học</div>
  }

  return (
    <div className="lesson-detail-page">
      <div className="lesson-header">
        <h1>{lesson.title}</h1>
        <span className={`difficulty-badge ${lesson.difficulty_level?.toLowerCase()}`}>
          {lesson.difficulty_level}
        </span>
      </div>

      <div className="lesson-content">
        <div className="lesson-description">
          <h2>Mô tả</h2>
          <p>{lesson.description}</p>
        </div>

        {lesson.content && (
          <div className="lesson-body">
            <h2>Nội dung</h2>
            <div dangerouslySetInnerHTML={{ __html: lesson.content }} />
          </div>
        )}

        {lesson.chart_start_time && (
          <div className="lesson-chart-section">
            <h2>Biểu đồ thực hành</h2>
            <p>Chart sẽ được hiển thị ở đây...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default LessonDetailPage

