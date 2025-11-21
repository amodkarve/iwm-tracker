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
    
    setLoading(false)
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

  const logout = async () => {
    try {
      if (token) {
        await axios.post('/api/auth/logout', {}, {
          headers: { Authorization: `Bearer ${token}` },
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

  const value = {
    isAuthenticated,
    loading,
    token,
    username,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

