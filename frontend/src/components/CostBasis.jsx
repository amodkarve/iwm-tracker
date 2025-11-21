import { useState, useEffect } from 'react'
import axios from 'axios'

export default function CostBasis() {
  const [costBasis, setCostBasis] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCostBasis()
  }, [])

  const fetchCostBasis = async () => {
    try {
      const response = await axios.get('/api/analytics/cost-basis')
      setCostBasis(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching cost basis:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return <div>Loading cost basis...</div>
  }

  if (costBasis.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        No cost basis data available. Add some trades first.
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">💰 Cost Basis Analysis</h2>
      
      <div className="space-y-6">
        {costBasis.map((basis) => (
          <div key={basis.symbol} className="bg-white rounded-lg border border-slate-200 p-6">
            <h3 className="text-lg font-semibold mb-4">📈 {basis.symbol} Position</h3>
            
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="metric-card">
                <div className="metric-label">📊 Shares</div>
                <div className="metric-value">
                  {basis.shares >= 0 ? '🟢' : '🔴'} {basis.shares.toFixed(0)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">💵 Basis (excl. premium)</div>
                <div className="metric-value">
                  ${basis.basis_without_premium.toFixed(2)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">🎯 Basis (incl. premium)</div>
                <div className="metric-value">
                  ${basis.basis_with_premium.toFixed(2)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">💎 Net Premium</div>
                <div className="metric-value">
                  {basis.net_premium >= 0 ? '🟢' : '🔴'} $
                  {basis.net_premium.toFixed(2)}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">💰 Total PnL</div>
                <div className="metric-value">
                  {basis.total_pnl >= 0 ? '🟢' : '🔴'} ${basis.total_pnl.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

