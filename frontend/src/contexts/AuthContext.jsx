import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext()

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(null)
  const [username, setUsername] = useState(null)

  const logout = async (currentToken = null) => {
    try {
      const tokenToUse = currentToken || token
      if (tokenToUse) {
        await axios.post('/api/auth/logout', {}, {
          headers: { Authorization: `Bearer ${tokenToUse}` },
        })
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      setToken(null)
      setUsername(null)
      setIsAuthenticated(false)
      delete axios.defaults.headers.common['Authorization']
    }
  }

  useEffect(() => {
    // Check for stored token
    const storedToken = localStorage.getItem('token')
    const storedUsername = localStorage.getItem('username')
    
    if (storedToken && storedUsername) {
      setToken(storedToken)
      setUsername(storedUsername)
      setIsAuthenticated(true)
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
    }
    
    // Add axios interceptor to handle token expiration
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid - logout
          const currentToken = localStorage.getItem('token')
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          setToken(null)
          setUsername(null)
          setIsAuthenticated(false)
          delete axios.defaults.headers.common['Authorization']
          
          // Try to logout on server (but don't wait for it)
          if (currentToken) {
            axios.post('/api/auth/logout', {}, {
              headers: { Authorization: `Bearer ${currentToken}` },
            }).catch(() => {}) // Ignore errors
          }
          
          // Redirect to login if not already there
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }
        return Promise.reject(error)
      }
    )
    
    setLoading(false)
    
    // Cleanup interceptor on unmount
    return () => {
      axios.interceptors.response.eject(interceptor)
    }
  }, [])

  const login = async (username, password) => {
    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password,
      })
      
      const { access_token, username: user } = response.data
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('username', user)
      setToken(access_token)
      setUsername(user)
      setIsAuthenticated(true)
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      }
    }
  }

  const handleLogout = async () => {
    await logout()
  }

  const value = {
    isAuthenticated,
    loading,
    token,
    username,
    login,
    logout: handleLogout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

