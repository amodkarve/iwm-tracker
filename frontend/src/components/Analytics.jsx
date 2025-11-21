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
  const [openPositions, setOpenPositions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAnalytics()
  }, [])

  const fetchAnalytics = async () => {
    try {
      const [monthlyRes, cumulativeRes, positionsRes] = await Promise.all([
        axios.get('/api/analytics/monthly-premium'),
        axios.get('/api/analytics/cumulative-premium'),
        axios.get('/api/analytics/open-positions'),
      ])

      setMonthlyPremium(monthlyRes.data)
      setCumulativePremium(cumulativeRes.data)
      setOpenPositions(positionsRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching analytics:', error)
      setLoading(false)
    }
  }

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

      {/* Open Positions */}
      {openPositions.length > 0 ? (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold mb-4">⚠️ Open Option Obligations</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                    Strike
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                    Expiration
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">
                    Net Quantity
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {openPositions.map((pos, index) => (
                  <tr key={index} className="hover:bg-slate-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                      {pos.symbol}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {pos.option_type.toUpperCase()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      ${pos.strike_price.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{pos.expiration_date}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          pos.net_quantity < 0
                            ? 'bg-red-100 text-red-800'
                            : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {pos.net_quantity > 0 ? '+' : ''}
                        {pos.net_quantity.toFixed(0)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800 text-center">
          🎉 No Open Option Obligations - All positions are closed!
        </div>
      )}
    </div>
  )
}

