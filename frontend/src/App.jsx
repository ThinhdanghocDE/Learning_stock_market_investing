import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout/Layout'
import AdminLayout from './components/AdminLayout/AdminLayout'
import Homepage from './pages/Homepage/Homepage'
import LoginPage from './pages/Auth/LoginPage'
import RegisterPage from './pages/Auth/RegisterPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import TradingPage from './pages/Trading/TradingPage'
import LearningPage from './pages/Learning/LearningPage'
import LessonDetailPage from './pages/Learning/LessonDetailPage'
import PortfolioPage from './pages/Portfolio/PortfolioPage'
import ExchangePage from './pages/Exchange/ExchangePage'
import AdminHomepagePage from './pages/Admin/AdminHomepagePage'
import AdminLessonsPage from './pages/Admin/AdminLessonsPage'
import AdminUsersPage from './pages/Admin/AdminUsersPage'
import AdminStatsPage from './pages/Admin/AdminStatsPage'
import ProtectedRoute from './components/Auth/ProtectedRoute'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/trading" /> : <Homepage />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/trading" /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/trading" /> : <RegisterPage />} />

      {/* Protected routes - User Layout */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Navigate to="/trading" />} /> {/* Tạm ẩn Dashboard */}
        <Route path="/trading" element={<TradingPage />} />
        <Route path="/learning" element={<LearningPage />} />
        <Route path="/learning/:lessonId" element={<LessonDetailPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/exchange" element={<ExchangePage />} />
      </Route>

      {/* Admin routes - Admin Layout with Sidebar */}
      <Route element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
        <Route path="/admin/homepage" element={<AdminHomepagePage />} />
        <Route path="/admin/lessons" element={<AdminLessonsPage />} />
        <Route path="/admin/users" element={<AdminUsersPage />} />
        <Route path="/admin/stats" element={<AdminStatsPage />} />
        <Route path="/admin" element={<Navigate to="/admin/lessons" />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
