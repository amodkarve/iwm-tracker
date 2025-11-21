import { createContext, useContext, useState, useEffect, useRef } from 'react'
import axios from 'axios'

const DatabaseContext = createContext()

export function useDatabase() {
  return useContext(DatabaseContext)
}

export function DatabaseProvider({ children }) {
  const [dbMode, setDbMode] = useState('prod') // 'prod' or 'test'
  const interceptorId = useRef(null)

  // Get the database path based on mode
  const getDbPath = () => {
    if (dbMode === 'test') {
      return '/app/data/wheel_test.db'
    }
    return null // null means use default (production)
  }

  useEffect(() => {
    // Load saved preference from localStorage
    const savedMode = localStorage.getItem('dbMode')
    if (savedMode === 'prod' || savedMode === 'test') {
      setDbMode(savedMode)
    }
    
    // Fetch database paths from backend (optional)
    const fetchDatabasePaths = async () => {
      try {
        await axios.get('/api/config/database/paths')
      } catch (error) {
        console.error('Error fetching database paths:', error)
      }
    }
    fetchDatabasePaths()
  }, [])

  // Set up axios interceptor to add db_path to all requests
  useEffect(() => {
    const path = getDbPath()
    
    // Remove old interceptor if it exists
    if (interceptorId.current !== null) {
      axios.interceptors.request.eject(interceptorId.current)
    }
    
    // Add new interceptor
    interceptorId.current = axios.interceptors.request.use(
      (config) => {
        // Add db_path as query parameter if test mode
        if (path && (config.method === 'get' || config.method === 'post' || config.method === 'put' || config.method === 'patch')) {
          config.params = {
            ...config.params,
            db_path: path,
          }
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )
    
    // Cleanup on unmount
    return () => {
      if (interceptorId.current !== null) {
        axios.interceptors.request.eject(interceptorId.current)
        interceptorId.current = null
      }
    }
  }, [dbMode])

  const switchDatabase = (mode) => {
    if (mode !== 'prod' && mode !== 'test') {
      console.error('Invalid database mode:', mode)
      return
    }
    
    setDbMode(mode)
    localStorage.setItem('dbMode', mode)
    
    // Trigger a refresh event so components can reload data
    window.dispatchEvent(new CustomEvent('databaseSwitched', { detail: { mode } }))
  }

  const value = {
    dbMode,
    dbPath: getDbPath(),
    isProduction: dbMode === 'prod',
    switchDatabase,
  }

  return <DatabaseContext.Provider value={value}>{children}</DatabaseContext.Provider>
}
