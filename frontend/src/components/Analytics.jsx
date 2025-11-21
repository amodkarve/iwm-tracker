import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

export default function Analytics() {
  const [monthlyPremium, setMonthlyPremium] = useState([])
  const [cumulativePremium, setCumulativePremium] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const [monthlyRes, cumulativeRes] = await Promise.all([
        axios.get('/api/analytics/monthly-premium'),
        axios.get('/api/analytics/cumulative-premium'),
      ])

      setMonthlyPremium(monthlyRes.data)
      setCumulativePremium(cumulativeRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching analytics:', error)
      setLoading(false)
    }
  }

  // Listen for trade added event to refresh
  useEffect(() => {
    const handleTradeAdded = () => {
      fetchAnalytics()
    }
    window.addEventListener('tradeAdded', handleTradeAdded)
    return () => {
      window.removeEventListener('tradeAdded', handleTradeAdded)
    }
  }, [])

  if (loading) {
    return <div>Loading analytics...</div>
  }

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold">📈 Analytics & Insights</h2>

      {/* Monthly Premium Chart */}
      {monthlyPremium.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold mb-4">📊 Monthly Net Premium</h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={monthlyPremium}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
              <Legend />
              <Bar
                dataKey="premium"
                fill={monthlyPremium[0]?.premium > 0 ? '#00ff88' : '#ff4444'}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Cumulative Premium Chart */}
      {cumulativePremium.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold mb-4">📈 Cumulative Net Premium</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={cumulativePremium}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
              <Legend />
              <Line
                type="monotone"
                dataKey="cumulative_premium"
                stroke="#667eea"
                strokeWidth={3}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

    </div>
  )
}

