import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../utils/api'
import './Learning.css'

function LearningPage() {
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)
  const [progressMap, setProgressMap] = useState({})

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch lessons
        const lessonsResponse = await api.get('/lessons')
        setLessons(lessonsResponse.data)

        // Try to fetch user progress
        try {
          const progressResponse = await api.get('/lessons/progress/all')
          const map = {}
          progressResponse.data.forEach(p => {
            map[p.lesson_id] = p
          })
          setProgressMap(map)
        } catch (err) {
          // User might not be logged in or no progress yet
          console.log('Could not fetch progress:', err)
        }
      } catch (error) {
        console.error('Error fetching lessons:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const getStatusBadge = (progress) => {
    if (!progress) return null

    switch (progress.status) {
      case 'COMPLETED':
        return <span className="status-badge completed">Hoàn thành</span>
      case 'IN_PROGRESS':
        return <span className="status-badge in-progress">Đang học</span>
      default:
        return null
    }
  }

  const getStarsDisplay = (lesson, progress) => {
    const earned = progress?.stars_earned || 0
    const total = lesson.stars_reward || 1000

    if (earned > 0) {
      return (
        <span className="stars-earned">
          {earned.toLocaleString()} sao
        </span>
      )
    }
    return (
      <span className="stars-potential">
        +{total.toLocaleString()} sao
      </span>
    )
  }

  if (loading) {
    return <div className="loading">Đang tải...</div>
  }

  return (
    <div className="learning-page">
      <div className="page-header">
        <h1 className="page-title">Học Tập</h1>
        <p className="page-subtitle">Chọn bài học để bắt đầu hành trình đầu tư</p>
      </div>

      <div className="lessons-grid">
        {lessons.map((lesson) => {
          const progress = progressMap[lesson.id]
          return (
            <Link
              key={lesson.id}
              to={`/learning/${lesson.id}`}
              className={`lesson-card ${progress?.status === 'COMPLETED' ? 'completed' : ''}`}
            >
              <div className="lesson-header">
                <h3>{lesson.title}</h3>
                <span className={`difficulty-badge ${lesson.difficulty_level?.toLowerCase()}`}>
                  {lesson.difficulty_level === 'BEGINNER' ? 'Cơ bản' :
                    lesson.difficulty_level === 'INTERMEDIATE' ? 'Trung bình' : 'Nâng cao'}
                </span>
              </div>

              <p className="lesson-description">{lesson.description}</p>

              <div className="lesson-footer">
                <div className="lesson-meta">
                  {lesson.required_points > 0 && (
                    <span className="required-points">
                      Yêu cầu: {lesson.required_points.toLocaleString()} điểm
                    </span>
                  )}
                  {lesson.quiz_data && (
                    <span className="has-quiz">Có Quiz</span>
                  )}
                  {lesson.content?.sections?.some(s => s.type === 'chart_practice') && (
                    <span className="has-chart">Thực hành Chart</span>
                  )}
                </div>
                <div className="lesson-status">
                  {getStatusBadge(progress)}
                  {getStarsDisplay(lesson, progress)}
                </div>
              </div>

              {progress?.quiz_passed && (
                <div className="quiz-result">
                  Quiz: {progress.quiz_score}/10
                </div>
              )}
            </Link>
          )
        })}
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
