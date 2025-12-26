import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../utils/api'
import './Admin.css'

function AdminLessonsPage() {
    const navigate = useNavigate()
    const [lessons, setLessons] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [showForm, setShowForm] = useState(false)
    const [editingLesson, setEditingLesson] = useState(null)
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        difficulty_level: 'BEGINNER',
        stars_reward: 1000,
        required_points: 0,
        order_index: 0,
        is_active: true,
        content: { sections: [] },
        quiz_data: { questions: [], passing_score: 8, total_questions: 10 },
    })

    useEffect(() => {
        fetchLessons()
    }, [])

    const fetchLessons = async () => {
        try {
            const response = await api.get('/admin/lessons')
            setLessons(response.data)
        } catch (err) {
            setError('Không thể tải danh sách bài học')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const handleCreate = () => {
        setEditingLesson(null)
        setFormData({
            title: '',
            description: '',
            difficulty_level: 'BEGINNER',
            stars_reward: 1000,
            required_points: 0,
            order_index: lessons.length,
            is_active: true,
            content: { sections: [] },
            quiz_data: { questions: [], passing_score: 8, total_questions: 10 },
        })
        setShowForm(true)
    }

    const handleEdit = (lesson) => {
        setEditingLesson(lesson)
        setFormData({
            title: lesson.title || '',
            description: lesson.description || '',
            difficulty_level: lesson.difficulty_level || 'BEGINNER',
            stars_reward: lesson.stars_reward || 1000,
            required_points: lesson.required_points || 0,
            order_index: lesson.order_index || 0,
            is_active: lesson.is_active !== false,
            content: lesson.content || { sections: [] },
            quiz_data: lesson.quiz_data || { questions: [], passing_score: 8, total_questions: 10 },
        })
        setShowForm(true)
    }

    const handleDelete = async (id) => {
        if (!window.confirm('Bạn có chắc muốn xóa bài học này?')) return

        try {
            await api.delete(`/admin/lessons/${id}`)
            fetchLessons()
        } catch (err) {
            alert('Không thể xóa bài học')
            console.error(err)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()

        try {
            if (editingLesson) {
                await api.put(`/admin/lessons/${editingLesson.id}`, formData)
            } else {
                await api.post('/admin/lessons', formData)
            }
            setShowForm(false)
            fetchLessons()
        } catch (err) {
            alert('Không thể lưu bài học')
            console.error(err)
        }
    }

    const handleDifficultyChange = (level) => {
        const starsMap = { BEGINNER: 1000, INTERMEDIATE: 2000, ADVANCED: 3000 }
        setFormData({
            ...formData,
            difficulty_level: level,
            stars_reward: starsMap[level],
        })
    }

    // Content Section Helpers
    const addSection = (type) => {
        const newSection = { type }
        if (type === 'text') newSection.content = ''
        if (type === 'video') {
            newSection.url = ''
            newSection.title = ''
        }
        if (type === 'image') {
            newSection.url = ''
            newSection.caption = ''
        }
        if (type === 'chart_practice') {
            newSection.symbol = 'ACB'
            newSection.start_date = new Date().toISOString().split('T')[0]
            newSection.duration_days = 7
            newSection.instructions = ''
        }

        setFormData({
            ...formData,
            content: {
                ...formData.content,
                sections: [...(formData.content.sections || []), newSection],
            },
        })
    }

    const updateSection = (index, field, value) => {
        const sections = [...formData.content.sections]
        sections[index] = { ...sections[index], [field]: value }
        setFormData({
            ...formData,
            content: { ...formData.content, sections },
        })
    }

    const removeSection = (index) => {
        const sections = formData.content.sections.filter((_, i) => i !== index)
        setFormData({
            ...formData,
            content: { ...formData.content, sections },
        })
    }

    const moveSectionUp = (index) => {
        if (index === 0) return
        const sections = [...formData.content.sections]
        const temp = sections[index - 1]
        sections[index - 1] = sections[index]
        sections[index] = temp
        setFormData({
            ...formData,
            content: { ...formData.content, sections },
        })
    }

    const moveSectionDown = (index) => {
        const sections = [...formData.content.sections]
        if (index >= sections.length - 1) return
        const temp = sections[index + 1]
        sections[index + 1] = sections[index]
        sections[index] = temp
        setFormData({
            ...formData,
            content: { ...formData.content, sections },
        })
    }

    // Quiz Helpers
    const addQuestion = () => {
        const newQuestion = {
            question: '',
            options: ['', '', '', ''],
            correct_answer: 0,
            explanation: '',
        }
        setFormData({
            ...formData,
            quiz_data: {
                ...formData.quiz_data,
                questions: [...(formData.quiz_data.questions || []), newQuestion],
                total_questions: (formData.quiz_data.questions?.length || 0) + 1,
            },
        })
    }

    const updateQuestion = (index, field, value) => {
        const questions = [...formData.quiz_data.questions]
        questions[index] = { ...questions[index], [field]: value }
        setFormData({
            ...formData,
            quiz_data: { ...formData.quiz_data, questions },
        })
    }

    const updateQuestionOption = (qIndex, oIndex, value) => {
        const questions = [...formData.quiz_data.questions]
        questions[qIndex].options[oIndex] = value
        setFormData({
            ...formData,
            quiz_data: { ...formData.quiz_data, questions },
        })
    }

    const removeQuestion = (index) => {
        const questions = formData.quiz_data.questions.filter((_, i) => i !== index)
        setFormData({
            ...formData,
            quiz_data: {
                ...formData.quiz_data,
                questions,
                total_questions: questions.length,
            },
        })
    }

    if (loading) return <div className="admin-loading">Đang tải...</div>

    return (
        <div className="admin-page">
            <div className="admin-header">
                <h1>Quản lý Bài học</h1>
                <button className="btn-primary" onClick={handleCreate}>
                    + Tạo bài học mới
                </button>
            </div>

            {error && <div className="admin-error">{error}</div>}

            {/* Lessons Table */}
            <div className="admin-table-container">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Tiêu đề</th>
                            <th>Độ khó</th>
                            <th>Sao</th>
                            <th>Điểm yêu cầu</th>
                            <th>Trạng thái</th>
                            <th>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lessons.map((lesson) => (
                            <tr key={lesson.id}>
                                <td>{lesson.id}</td>
                                <td>{lesson.title}</td>
                                <td>
                                    <span className={`difficulty-badge ${lesson.difficulty_level?.toLowerCase()}`}>
                                        {lesson.difficulty_level}
                                    </span>
                                </td>
                                <td>{lesson.stars_reward?.toLocaleString()}</td>
                                <td>{lesson.required_points}</td>
                                <td>
                                    <span className={`status-badge ${lesson.is_active ? 'active' : 'inactive'}`}>
                                        {lesson.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                </td>
                                <td>
                                    <div className="action-buttons">
                                        <button className="btn-edit" onClick={() => handleEdit(lesson)}>
                                            Sửa
                                        </button>
                                        <button className="btn-delete" onClick={() => handleDelete(lesson.id)}>
                                            Xóa
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Form Modal */}
            {showForm && (
                <div className="modal-overlay">
                    <div className="modal-content lesson-form-modal">
                        <div className="modal-header">
                            <h2>{editingLesson ? 'Sửa bài học' : 'Tạo bài học mới'}</h2>
                            <button className="btn-close" onClick={() => setShowForm(false)}>×</button>
                        </div>

                        <form onSubmit={handleSubmit} className="lesson-form">
                            {/* Basic Info */}
                            <div className="form-section">
                                <h3>Thông tin cơ bản</h3>
                                <div className="form-group">
                                    <label>Tiêu đề *</label>
                                    <input
                                        type="text"
                                        value={formData.title}
                                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                        required
                                    />
                                </div>

                                <div className="form-group">
                                    <label>Mô tả</label>
                                    <textarea
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        rows={3}
                                    />
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Độ khó</label>
                                        <select
                                            value={formData.difficulty_level}
                                            onChange={(e) => handleDifficultyChange(e.target.value)}
                                        >
                                            <option value="BEGINNER">Cơ bản (1000 sao)</option>
                                            <option value="INTERMEDIATE">Trung bình (2000 sao)</option>
                                            <option value="ADVANCED">Nâng cao (3000 sao)</option>
                                        </select>
                                    </div>

                                    <div className="form-group">
                                        <label>Điểm yêu cầu</label>
                                        <input
                                            type="number"
                                            value={formData.required_points}
                                            onChange={(e) => setFormData({ ...formData, required_points: parseInt(e.target.value) || 0 })}
                                            min={0}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Thứ tự</label>
                                        <input
                                            type="number"
                                            value={formData.order_index}
                                            onChange={(e) => setFormData({ ...formData, order_index: parseInt(e.target.value) || 0 })}
                                            min={0}
                                        />
                                    </div>
                                </div>

                                <div className="form-group checkbox">
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={formData.is_active}
                                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                        />
                                        Kích hoạt bài học
                                    </label>
                                </div>
                            </div>

                            {/* Content Sections */}
                            <div className="form-section">
                                <h3>Nội dung bài học</h3>
                                <div className="section-buttons">
                                    <button type="button" onClick={() => addSection('text')}>+ Text</button>
                                    <button type="button" onClick={() => addSection('video')}>+ Video</button>
                                    <button type="button" onClick={() => addSection('image')}>+ Image</button>
                                    <button type="button" onClick={() => addSection('chart_practice')}>+ Chart</button>
                                </div>

                                {formData.content.sections?.map((section, index) => (
                                    <div key={index} className="content-section-editor">
                                        <div className="section-header">
                                            <span className="section-type">{index + 1}. {section.type.toUpperCase()}</span>
                                            <div className="section-actions">
                                                <button
                                                    type="button"
                                                    onClick={() => moveSectionUp(index)}
                                                    disabled={index === 0}
                                                    title="Di chuyển lên"
                                                >
                                                    ↑
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => moveSectionDown(index)}
                                                    disabled={index === formData.content.sections.length - 1}
                                                    title="Di chuyển xuống"
                                                >
                                                    ↓
                                                </button>
                                                <button type="button" className="btn-remove" onClick={() => removeSection(index)}>Xóa</button>
                                            </div>
                                        </div>

                                        {section.type === 'text' && (
                                            <textarea
                                                value={section.content}
                                                onChange={(e) => updateSection(index, 'content', e.target.value)}
                                                placeholder="Nội dung markdown..."
                                                rows={5}
                                            />
                                        )}

                                        {section.type === 'video' && (
                                            <>
                                                <input
                                                    type="text"
                                                    value={section.url}
                                                    onChange={(e) => updateSection(index, 'url', e.target.value)}
                                                    placeholder="YouTube URL"
                                                />
                                                <input
                                                    type="text"
                                                    value={section.title || ''}
                                                    onChange={(e) => updateSection(index, 'title', e.target.value)}
                                                    placeholder="Tiêu đề video"
                                                />
                                            </>
                                        )}

                                        {section.type === 'image' && (
                                            <>
                                                <input
                                                    type="text"
                                                    value={section.url}
                                                    onChange={(e) => updateSection(index, 'url', e.target.value)}
                                                    placeholder="Image URL"
                                                />
                                                <input
                                                    type="text"
                                                    value={section.caption || ''}
                                                    onChange={(e) => updateSection(index, 'caption', e.target.value)}
                                                    placeholder="Caption"
                                                />
                                            </>
                                        )}

                                        {section.type === 'chart_practice' && (
                                            <div className="chart-practice-fields">
                                                <input
                                                    type="text"
                                                    value={section.symbol}
                                                    onChange={(e) => updateSection(index, 'symbol', e.target.value)}
                                                    placeholder="Symbol (VD: ACB)"
                                                />
                                                <input
                                                    type="date"
                                                    value={section.start_date}
                                                    onChange={(e) => updateSection(index, 'start_date', e.target.value)}
                                                />
                                                <input
                                                    type="number"
                                                    value={section.duration_days}
                                                    onChange={(e) => updateSection(index, 'duration_days', parseInt(e.target.value) || 7)}
                                                    placeholder="Số ngày"
                                                    min={1}
                                                />
                                                <input
                                                    type="text"
                                                    value={section.instructions || ''}
                                                    onChange={(e) => updateSection(index, 'instructions', e.target.value)}
                                                    placeholder="Hướng dẫn thực hành"
                                                />
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Quiz */}
                            <div className="form-section">
                                <h3>Quiz</h3>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Điểm qua</label>
                                        <input
                                            type="number"
                                            value={formData.quiz_data.passing_score}
                                            onChange={(e) => setFormData({
                                                ...formData,
                                                quiz_data: { ...formData.quiz_data, passing_score: parseInt(e.target.value) || 8 }
                                            })}
                                            min={1}
                                            max={10}
                                        />
                                    </div>
                                </div>

                                <button type="button" className="btn-add-question" onClick={addQuestion}>
                                    + Thêm câu hỏi
                                </button>

                                {formData.quiz_data.questions?.map((question, qIndex) => (
                                    <div key={qIndex} className="question-editor">
                                        <div className="question-header">
                                            <span>Câu {qIndex + 1}</span>
                                            <button type="button" onClick={() => removeQuestion(qIndex)}>Xóa</button>
                                        </div>

                                        <textarea
                                            value={question.question}
                                            onChange={(e) => updateQuestion(qIndex, 'question', e.target.value)}
                                            placeholder="Nội dung câu hỏi"
                                            rows={2}
                                        />

                                        <div className="options-editor">
                                            {question.options.map((option, oIndex) => (
                                                <div key={oIndex} className="option-row">
                                                    <input
                                                        type="radio"
                                                        name={`correct-${qIndex}`}
                                                        checked={question.correct_answer === oIndex}
                                                        onChange={() => updateQuestion(qIndex, 'correct_answer', oIndex)}
                                                    />
                                                    <input
                                                        type="text"
                                                        value={option}
                                                        onChange={(e) => updateQuestionOption(qIndex, oIndex, e.target.value)}
                                                        placeholder={`Đáp án ${String.fromCharCode(65 + oIndex)}`}
                                                    />
                                                </div>
                                            ))}
                                        </div>

                                        <input
                                            type="text"
                                            value={question.explanation || ''}
                                            onChange={(e) => updateQuestion(qIndex, 'explanation', e.target.value)}
                                            placeholder="Giải thích (tùy chọn)"
                                        />
                                    </div>
                                ))}
                            </div>

                            <div className="form-actions">
                                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>
                                    Hủy
                                </button>
                                <button type="submit" className="btn-primary">
                                    {editingLesson ? 'Cập nhật' : 'Tạo mới'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}

export default AdminLessonsPage
