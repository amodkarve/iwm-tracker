import { useState, useEffect } from 'react'
import axios from 'axios'
import TradeForm from './TradeForm'

export default function Recommendations({ accountSize }) {
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchRecommendations = async () => {
    try {
      const response = await axios.get('/api/recommendations/all', {
        params: { account_value: accountSize, max_recommendations: 10 },
      })
      setRecommendations(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching recommendations:', error)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRecommendations()
    
    // Listen for trade added/closed events to refresh
    const handleTradeAdded = () => {
      fetchRecommendations()
    }
    window.addEventListener('tradeAdded', handleTradeAdded)
    
    return () => {
      window.removeEventListener('tradeAdded', handleTradeAdded)
    }
  }, [accountSize])

  if (loading) {
    return <div>Loading recommendations...</div>
  }

  const actionIcons = {
    ROLL: '🔄',
    HEDGE: '🛡️',
    SUBSTITUTE: '🔄',
    OPEN_COVERED_CALL: '📞',
    OPEN_PUT: '📉',
  }

  const confidenceColors = {
    high: '🟢',
    medium: '🟡',
    low: '🔴',
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">💡 Comprehensive Trade Recommendations</h2>
      
      {recommendations.length === 0 ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          No recommendations available. Check market data connection.
        </div>
      ) : (
        <div className="space-y-4">
          {recommendations.map((rec, index) => (
            <div
              key={index}
              className="bg-white border border-slate-200 rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                  {confidenceColors[rec.confidence] || '⚪'}{' '}
                  {actionIcons[rec.action_type] || '📊'}{' '}
                  {rec.action_type.replace(/_/g, ' ')} - Strike ${rec.strike.toFixed(2)} (
                  {rec.confidence.toUpperCase()})
                </h3>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <div className="text-sm text-slate-600">Strike Price</div>
                  <div className="text-lg font-semibold">${rec.strike.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">Bid/Ask</div>
                  <div className="text-lg font-semibold">
                    ${rec.bid.toFixed(2)} / ${rec.ask.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">Mid Price</div>
                  <div className="text-lg font-semibold">${rec.mid.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">Recommended Contracts</div>
                  <div className="text-lg font-semibold">{rec.recommended_contracts}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">
                    {rec.expected_premium > 0 ? 'Net Credit' : 'Cost'}
                  </div>
                  <div className="text-lg font-semibold">
                    ${Math.abs(rec.expected_premium).toFixed(0)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-slate-600">% of Account</div>
                  <div className="text-lg font-semibold">
                    {(Math.abs(rec.premium_pct) * 100).toFixed(3)}%
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
                <div className="text-sm font-medium text-blue-900">Analysis:</div>
                <div className="text-sm text-blue-800">{rec.reason}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

