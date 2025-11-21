import { useState, useEffect } from 'react'
import axios from 'axios'

export default function PerformanceMetrics({ accountSize }) {
  const [performance, setPerformance] = useState(null)
  const [capitalUsage, setCapitalUsage] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPerformance()
  }, [accountSize])

  const [error, setError] = useState(null)

  const fetchPerformance = async () => {
    try {
      setError(null)
      const [perfRes, capitalRes] = await Promise.all([
        axios.get('/api/analytics/performance', {
          params: { account_value: accountSize, initial_value: accountSize },
        }),
        axios.get('/api/analytics/capital-usage', {
          params: { account_size: accountSize },
        }),
      ])

      setPerformance(perfRes.data)
      setCapitalUsage(capitalRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching performance:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch performance data'
      setError(errorMessage)
      setLoading(false)
    }
  }

  if (loading) {
    return <div>Loading performance metrics...</div>
  }

  if (error) {
    return (
      <div>
        <h2 className="text-xl font-bold mb-4">🎯 Performance Tracking</h2>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <div className="font-semibold mb-2">Error loading performance data</div>
          <div className="text-sm">{error}</div>
        </div>
      </div>
    )
  }

  if (!performance) {
    return (
      <div>
        <h2 className="text-xl font-bold mb-4">🎯 Performance Tracking</h2>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          No performance data available. Add some trades to see performance metrics.
        </div>
      </div>
    )
  }

  const annualReturnPct = (performance.annualized_return * 100).toFixed(2)
  const isOnTrack = performance.on_track
  const bpUsage = (capitalUsage?.buying_power_usage_pct * 100).toFixed(1)

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">🎯 Performance Tracking</h2>
      
      {/* Performance Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="metric-card">
          <div className="metric-label">Annualized Return</div>
          <div className="metric-value">
            {isOnTrack ? '🟢' : '🔴'} {annualReturnPct}%
          </div>
          <div className="text-xs text-slate-500 mt-1">Target: 18-20%</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Premium</div>
          <div className="metric-value">
            ${performance.total_premium.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <div className="text-xs text-slate-500 mt-1">All time</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Win Rate</div>
          <div className="metric-value">
            {(performance.win_rate * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {performance.total_trades} closed trades
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Avg Win</div>
          <div className="metric-value">
            ${performance.avg_win.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <div className="text-xs text-slate-500 mt-1">Per trade</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Days Active</div>
          <div className="metric-value">{performance.days_active}</div>
          <div className="text-xs text-slate-500 mt-1">Trading days</div>
        </div>
      </div>

      {/* Capital Usage */}
      {capitalUsage && (
        <div className="bg-white rounded-lg border border-slate-200 p-6">
          <h3 className="text-lg font-semibold mb-4">💰 Capital & Buying Power</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-700">
                  Buying Power Used
                </span>
                <span className="text-lg font-bold">{bpUsage}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2.5">
                <div
                  className={`h-2.5 rounded-full ${
                    parseFloat(bpUsage) < 50
                      ? 'bg-green-500'
                      : parseFloat(bpUsage) < 75
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(parseFloat(bpUsage), 100)}%` }}
                ></div>
              </div>
              <div className="text-sm text-slate-600 mt-1">
                ${capitalUsage.total_deployed.toLocaleString()} Deployed
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-slate-600">Cash Secured Puts:</span>{' '}
                <span className="font-medium">
                  ${capitalUsage.cash_secured_puts.toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-slate-600">Stock Position:</span>{' '}
                <span className="font-medium">
                  ${capitalUsage.long_stock.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

