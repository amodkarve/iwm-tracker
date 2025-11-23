import { useState, useEffect } from 'react'
import axios from 'axios'

export default function PortfolioNav() {
  const [navData, setNavData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchNav = async () => {
    try {
      setError(null)
      const response = await axios.get('/api/analytics/portfolio-nav')
      setNavData(response.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching portfolio NAV:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch portfolio NAV'
      setError(errorMessage)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNav()
    
    // Listen for trade added/closed events to refresh
    const handleTradeAdded = () => {
      fetchNav()
    }
    window.addEventListener('tradeAdded', handleTradeAdded)
    
    return () => {
      window.removeEventListener('tradeAdded', handleTradeAdded)
    }
  }, [])

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-4">💰 Portfolio NAV</h3>
        <div>Loading portfolio data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-4">💰 Portfolio NAV</h3>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <div className="font-semibold mb-2">Error loading portfolio NAV</div>
          <div className="text-sm">{error}</div>
        </div>
      </div>
    )
  }

  if (!navData) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h3 className="text-lg font-semibold mb-4">💰 Portfolio NAV</h3>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          No portfolio data available.
        </div>
      </div>
    )
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatCurrencyWithDecimals = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const totalReturn = navData.nav - navData.starting_value
  const totalReturnPct = navData.starting_value > 0 
    ? (totalReturn / navData.starting_value) * 100 
    : 0

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold mb-4">💰 Portfolio NAV</h3>
      
      <div className="space-y-4">
        {/* NAV Display */}
        <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
          <div className="text-sm text-slate-600 mb-1">Net Asset Value</div>
          <div className="text-3xl font-bold text-blue-900">
            {formatCurrency(navData.nav)}
          </div>
          <div className="text-sm text-slate-600 mt-2">
            Starting Value: {formatCurrency(navData.starting_value)}
          </div>
          <div className={`text-sm font-medium mt-1 ${
            totalReturn >= 0 ? 'text-green-700' : 'text-red-700'
          }`}>
            Total Return: {formatCurrencyWithDecimals(totalReturn)} ({totalReturnPct.toFixed(2)}%)
          </div>
        </div>

        {/* PnL Breakdown */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
            <div className="text-xs text-slate-500 mb-1">Open PnL</div>
            <div className={`text-xl font-bold ${
              navData.open_pnl >= 0 ? 'text-green-700' : 'text-red-700'
            }`}>
              {formatCurrencyWithDecimals(navData.open_pnl)}
            </div>
            <div className="text-xs text-slate-500 mt-1">Unrealized</div>
          </div>

          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
            <div className="text-xs text-slate-500 mb-1">Closed PnL</div>
            <div className={`text-xl font-bold ${
              navData.closed_pnl >= 0 ? 'text-green-700' : 'text-red-700'
            }`}>
              {formatCurrencyWithDecimals(navData.closed_pnl)}
            </div>
            <div className="text-xs text-slate-500 mt-1">Realized</div>
          </div>
        </div>

        {/* Formula Display */}
        <div className="text-xs text-slate-500 pt-2 border-t border-slate-200">
          NAV = Starting Value + Open PnL + Closed PnL
        </div>
      </div>
    </div>
  )
}

