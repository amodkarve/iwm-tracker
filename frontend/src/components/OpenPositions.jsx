import { useState, useEffect } from 'react'
import axios from 'axios'
import ClosePosition from './ClosePosition'

export default function OpenPositions() {
  const [openPositions, setOpenPositions] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedPositions, setExpandedPositions] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchOpenPositions()
    
    // Listen for trade added event to refresh
    const handleTradeAdded = () => {
      fetchOpenPositions()
    }
    window.addEventListener('tradeAdded', handleTradeAdded)
    
    return () => {
      window.removeEventListener('tradeAdded', handleTradeAdded)
    }
  }, [])

  const fetchOpenPositions = async () => {
    try {
      setError(null)
      const response = await axios.get('/api/analytics/open-positions')
      setOpenPositions(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching open positions:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch open positions'
      setError(errorMessage)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-4">⚠️ Open Option Obligations</h3>
        <div>Loading open positions...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-4">⚠️ Open Option Obligations</h3>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <div className="font-semibold mb-2">Error loading open positions</div>
          <div className="text-sm">{error}</div>
        </div>
      </div>
    )
  }

  if (openPositions.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-4">⚠️ Open Option Obligations</h3>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800 text-center">
          🎉 No Open Option Obligations - All positions are closed!
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold mb-4">⚠️ Open Option Obligations</h3>
      <div className="space-y-4">
        {openPositions.map((pos, index) => {
          const isShort = pos.net_quantity < 0
          const positionKey = `${pos.symbol}-${pos.strike_price}-${pos.expiration_date}-${pos.option_type}`
          const isExpanded = expandedPositions[positionKey] || false

          return (
            <div
              key={index}
              className="border border-slate-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 grid grid-cols-5 gap-4 items-center">
                  <div>
                    <div className="text-xs text-slate-500">Symbol</div>
                    <div className="font-semibold">{pos.symbol}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Type</div>
                    <div className="font-semibold">
                      {pos.option_type.toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Strike</div>
                    <div className="font-semibold">
                      ${pos.strike_price.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Expiration</div>
                    <div className="font-semibold">{pos.expiration_date}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Net Quantity</div>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        isShort
                          ? 'bg-red-100 text-red-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {pos.net_quantity > 0 ? '+' : ''}
                      {pos.net_quantity.toFixed(0)}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() =>
                    setExpandedPositions({
                      ...expandedPositions,
                      [positionKey]: !isExpanded,
                    })
                  }
                  className="ml-4 btn-secondary text-sm"
                >
                  {isExpanded ? 'Hide' : 'Manage'}
                </button>
              </div>

              {isExpanded && (
                <ClosePosition
                  position={pos}
                  onClose={() => {
                    setExpandedPositions({
                      ...expandedPositions,
                      [positionKey]: false,
                    })
                    fetchOpenPositions()
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

