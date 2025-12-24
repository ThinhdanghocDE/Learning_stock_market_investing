import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../utils/api'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (username, password) => {
        try {
          const formData = new FormData()
          formData.append('username', username)
          formData.append('password', password)

          const response = await api.post('/auth/login', formData, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          })

          const { access_token } = response.data
          
          // Lấy thông tin user
          const userResponse = await api.get('/auth/me', {
            headers: {
              Authorization: `Bearer ${access_token}`,
            },
          })

          set({
            token: access_token,
            user: userResponse.data,
            isAuthenticated: true,
          })

          // Set default authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          return { success: true }
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.detail || 'Đăng nhập thất bại',
          }
        }
      },

      register: async (username, email, password) => {
        try {
          const response = await api.post('/auth/register', {
            username,
            email,
            password,
          })

          // Tự động login sau khi register
          return await get().login(username, password)
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.detail || 'Đăng ký thất bại',
          }
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
        delete api.defaults.headers.common['Authorization']
      },

      checkAuth: async () => {
        const { token } = get()
        if (!token) {
          return false
        }

        try {
          const response = await api.get('/auth/me', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })

          set({
            user: response.data,
            isAuthenticated: true,
          })

          api.defaults.headers.common['Authorization'] = `Bearer ${token}`
          return true
        } catch (error) {
          get().logout()
          return false
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
)

export { useAuthStore }
export default useAuthStore

