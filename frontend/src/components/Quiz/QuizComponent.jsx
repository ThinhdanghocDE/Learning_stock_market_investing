import { useState } from 'react'
import api from '../../utils/api'
import './Quiz.css'

function QuizComponent({ lessonId, quizData, onComplete, onCancel }) {
    const [currentQuestion, setCurrentQuestion] = useState(0)
    const [answers, setAnswers] = useState([])
    const [selectedAnswer, setSelectedAnswer] = useState(null)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    const questions = quizData?.questions || []
    const totalQuestions = questions.length
    const question = questions[currentQuestion]

    const handleSelectAnswer = (index) => {
        setSelectedAnswer(index)
    }

    const handleNext = () => {
        if (selectedAnswer === null) return

        const newAnswers = [...answers, selectedAnswer]
        setAnswers(newAnswers)
        setSelectedAnswer(null)

        if (currentQuestion < totalQuestions - 1) {
            setCurrentQuestion(currentQuestion + 1)
        } else {
            // Submit quiz
            submitQuiz(newAnswers)
        }
    }

    const handlePrevious = () => {
        if (currentQuestion > 0) {
            setCurrentQuestion(currentQuestion - 1)
            setSelectedAnswer(answers[currentQuestion - 1] ?? null)
            setAnswers(answers.slice(0, -1))
        }
    }

    const submitQuiz = async (finalAnswers) => {
        setSubmitting(true)
        setError(null)

        try {
            const response = await api.post(`/lessons/${lessonId}/submit-quiz`, {
                answers: finalAnswers
            })
            onComplete(response.data)
        } catch (err) {
            setError(err.response?.data?.detail || 'Có lỗi xảy ra khi nộp quiz')
            setSubmitting(false)
        }
    }

    if (!question) {
        return <div className="quiz-error">Quiz không có câu hỏi</div>
    }

    return (
        <div className="quiz-container">
            <div className="quiz-header">
                <div className="quiz-progress">
                    <span>Câu {currentQuestion + 1}/{totalQuestions}</span>
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{ width: `${((currentQuestion + 1) / totalQuestions) * 100}%` }}
                        />
                    </div>
                </div>
                <button className="btn-cancel" onClick={onCancel}>
                    Hủy
                </button>
            </div>

            <div className="quiz-question">
                <h3>{question.question}</h3>

                <div className="quiz-options">
                    {question.options.map((option, index) => (
                        <button
                            key={index}
                            className={`quiz-option ${selectedAnswer === index ? 'selected' : ''}`}
                            onClick={() => handleSelectAnswer(index)}
                        >
                            <span className="option-letter">
                                {String.fromCharCode(65 + index)}
                            </span>
                            <span className="option-text">{option}</span>
                        </button>
                    ))}
                </div>
            </div>

            {error && <div className="quiz-error">{error}</div>}

            <div className="quiz-footer">
                <button
                    className="btn-secondary"
                    onClick={handlePrevious}
                    disabled={currentQuestion === 0}
                >
                    Câu trước
                </button>

                <button
                    className="btn-primary"
                    onClick={handleNext}
                    disabled={selectedAnswer === null || submitting}
                >
                    {submitting ? 'Đang nộp...' :
                        currentQuestion === totalQuestions - 1 ? 'Nộp bài' : 'Câu tiếp'}
                </button>
            </div>
        </div>
    )
}

export default QuizComponent
