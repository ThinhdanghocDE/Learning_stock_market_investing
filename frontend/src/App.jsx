import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout/Layout'
import LoginPage from './pages/Auth/LoginPage'
import RegisterPage from './pages/Auth/RegisterPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import TradingPage from './pages/Trading/TradingPage'
import LearningPage from './pages/Learning/LearningPage'
import LessonDetailPage from './pages/Learning/LessonDetailPage'
import PortfolioPage from './pages/Portfolio/PortfolioPage'
import AdminLessonsPage from './pages/Admin/AdminLessonsPage'
import ProtectedRoute from './components/Auth/ProtectedRoute'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterPage />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/trading" element={<TradingPage />} />
        <Route path="/learning" element={<LearningPage />} />
        <Route path="/learning/:lessonId" element={<LessonDetailPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/admin/lessons" element={<AdminLessonsPage />} />
      </Route>

      {/* Default redirect */}
      <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} />
      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  )
}

export default App


