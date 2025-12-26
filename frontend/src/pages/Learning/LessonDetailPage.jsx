import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../../utils/api'
import QuizComponent from '../../components/Quiz/QuizComponent'
import ChartPractice from '../../components/ChartPractice/ChartPractice'
import './Learning.css'

function LessonDetailPage() {
  const { lessonId } = useParams()
  const navigate = useNavigate()
  const [lesson, setLesson] = useState(null)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)
  const [canAccess, setCanAccess] = useState(true)
  const [accessError, setAccessError] = useState(null)
  const [showQuiz, setShowQuiz] = useState(false)
  const [quizResult, setQuizResult] = useState(null)

  useEffect(() => {
    const fetchLesson = async () => {
      try {
        // Fetch lesson with progress
        const response = await api.get(`/lessons/${lessonId}/with-progress`)
        setLesson(response.data.lesson)
        setProgress(response.data.progress)
        setCanAccess(response.data.can_access)
        setAccessError(response.data.access_error)

        // Start lesson if not started
        if (response.data.can_access && (!response.data.progress || response.data.progress.status === 'NOT_STARTED')) {
          await api.post(`/lessons/${lessonId}/start`)
        }
      } catch (error) {
        console.error('Error fetching lesson:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchLesson()
  }, [lessonId])

  const handleQuizComplete = useCallback((result) => {
    setQuizResult(result)
    if (result.passed) {
      // Refresh progress
      api.get(`/lessons/${lessonId}/with-progress`).then(res => {
        setProgress(res.data.progress)
      })
    }
  }, [lessonId])

  const renderSection = (section, index) => {
    switch (section.type) {
      case 'text':
        return (
          <div key={index} className="section-text">
            <div
              className="markdown-content"
              dangerouslySetInnerHTML={{ __html: formatMarkdown(section.content) }}
            />
          </div>
        )

      case 'video':
        return (
          <div key={index} className="section-video">
            {section.title && <h3>{section.title}</h3>}
            <div className="video-container">
              <iframe
                src={getYouTubeEmbedUrl(section.url)}
                title={section.title || 'Video bài học'}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          </div>
        )

      case 'image':
        return (
          <div key={index} className="section-image">
            <img src={section.url} alt={section.caption || 'Hình ảnh bài học'} />
            {section.caption && <p className="image-caption">{section.caption}</p>}
          </div>
        )

      case 'chart_practice':
        return (
          <div key={index} className="section-chart-practice">
            <h3>Thực hành trên Chart</h3>
            {section.instructions && (
              <p className="chart-instructions">{section.instructions}</p>
            )}
            <ChartPractice
              symbol={section.symbol}
              startDate={section.start_date}
              durationDays={section.duration_days || 7}
            />
          </div>
        )

      default:
        return null
    }
  }

  // Helper: Format basic markdown
  const formatMarkdown = (text) => {
    if (!text) return ''

    // Basic markdown conversion
    let html = text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*)\*/gim, '<em>$1</em>')
      .replace(/\n/gim, '<br>')

    return html
  }

  // Helper: Get YouTube embed URL
  const getYouTubeEmbedUrl = (url) => {
    if (!url) return ''

    // Extract video ID from various YouTube URL formats
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/
    const match = url.match(regExp)

    if (match && match[2].length === 11) {
      return `https://www.youtube.com/embed/${match[2]}`
    }

    return url
  }

  if (loading) {
    return <div className="loading">Đang tải...</div>
  }

  if (!lesson) {
    return <div className="error">Không tìm thấy bài học</div>
  }

  if (!canAccess) {
    return (
      <div className="lesson-locked">
        <h2>Bài học bị khóa</h2>
        <p>{accessError}</p>
        <button onClick={() => navigate('/learning')} className="btn-primary">
          Quay lại danh sách bài học
        </button>
      </div>
    )
  }

  const sections = lesson.content?.sections || []
  const hasQuiz = lesson.quiz_data?.questions?.length > 0

  return (
    <div className="lesson-detail-page">
      <div className="lesson-header">
        <div className="header-top">
          <button onClick={() => navigate('/learning')} className="btn-back">
            Quay lại
          </button>
          <span className={`difficulty-badge ${lesson.difficulty_level?.toLowerCase()}`}>
            {lesson.difficulty_level === 'BEGINNER' ? 'Cơ bản' :
              lesson.difficulty_level === 'INTERMEDIATE' ? 'Trung bình' : 'Nâng cao'}
          </span>
        </div>
        <h1>{lesson.title}</h1>
        {lesson.description && (
          <p className="lesson-subtitle">{lesson.description}</p>
        )}

        <div className="lesson-progress-bar">
          {progress?.quiz_passed ? (
            <div className="progress-complete">
              Đã hoàn thành - {progress.stars_earned?.toLocaleString()} sao
            </div>
          ) : (
            <div className="progress-pending">
              Hoàn thành quiz để nhận {lesson.stars_reward?.toLocaleString()} sao
            </div>
          )}
        </div>
      </div>

      <div className="lesson-content">
        {/* Render content sections */}
        {sections.map((section, index) => renderSection(section, index))}

        {/* Show quiz button or quiz result */}
        {hasQuiz && !showQuiz && !progress?.quiz_passed && (
          <div className="quiz-prompt">
            <h2>Kiểm tra kiến thức</h2>
            <p>Hoàn thành quiz để mở khóa bài học tiếp theo và nhận sao thưởng.</p>
            <p className="quiz-info">
              Số câu hỏi: {lesson.quiz_data.total_questions || lesson.quiz_data.questions.length} |
              Điểm qua: {lesson.quiz_data.passing_score || 8}/10
            </p>
            <button
              onClick={() => setShowQuiz(true)}
              className="btn-primary btn-start-quiz"
            >
              Bắt đầu Quiz
            </button>
          </div>
        )}

        {/* Quiz component */}
        {showQuiz && !quizResult && (
          <QuizComponent
            lessonId={lessonId}
            quizData={lesson.quiz_data}
            onComplete={handleQuizComplete}
            onCancel={() => setShowQuiz(false)}
          />
        )}

        {/* Quiz result */}
        {quizResult && (
          <div className={`quiz-result-card ${quizResult.passed ? 'passed' : 'failed'}`}>
            <h2>{quizResult.passed ? 'Chúc mừng!' : 'Chưa đạt'}</h2>
            <p className="quiz-score">
              Điểm: {quizResult.score}/{quizResult.total}
            </p>
            {quizResult.passed ? (
              <>
                <p className="stars-earned">+{quizResult.stars_earned.toLocaleString()} sao</p>
                <button
                  onClick={() => navigate('/learning')}
                  className="btn-primary"
                >
                  Tiếp tục học
                </button>
              </>
            ) : (
              <button
                onClick={() => {
                  setQuizResult(null)
                  setShowQuiz(true)
                }}
                className="btn-secondary"
              >
                Thử lại
              </button>
            )}
          </div>
        )}

        {/* Already passed */}
        {progress?.quiz_passed && (
          <div className="quiz-result-card passed">
            <h2>Bạn đã hoàn thành bài học này</h2>
            <p className="quiz-score">Điểm quiz: {progress.quiz_score}/10</p>
            <p className="stars-earned">Đã nhận: {progress.stars_earned?.toLocaleString()} sao</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default LessonDetailPage
