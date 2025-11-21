import { useState } from 'react'
import axios from 'axios'

export default function ConvertRecommendation({ recommendation, onClose, onSuccess }) {
  // Determine side based on action type
  const getSide = (actionType) => {
    if (actionType.includes('PUT') || actionType === 'OPEN_PUT' || actionType === 'HEDGE') {
      return 'sell' // Selling puts
    } else if (actionType === 'OPEN_COVERED_CALL') {
      return 'sell' // Selling covered calls
    }
    return 'sell' // Default to sell for most recommendations
  }

  // Format expiration date for API (YYYY-MM-DD)
  const formatDateForAPI = (dateValue) => {
    if (!dateValue) return null
    // If it's already a string in YYYY-MM-DD format, return it
    if (typeof dateValue === 'string') {
      if (dateValue.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return dateValue
      }
      // Try to parse it
      const date = new Date(dateValue)
      if (!isNaN(date.getTime())) {
        return date.toISOString().split('T')[0]
      }
    }
    // If it's a date object or datetime, convert it
    try {
      const date = new Date(dateValue)
      if (!isNaN(date.getTime())) {
        return date.toISOString().split('T')[0]
      }
    } catch (e) {
      console.error('Error formatting date:', e)
    }
    return null
  }

  const [formData, setFormData] = useState({
    quantity: recommendation.recommended_contracts || 1,
    price: recommendation.mid || recommendation.recommended_price || 0.0,
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const tradeData = {
        symbol: recommendation.symbol || 'IWM',
        quantity: formData.quantity,
        price: formData.price,
        side: getSide(recommendation.action_type),
        strategy: recommendation.action_type?.toLowerCase().replace(/_/g, '_') || 'wheel',
        expiration_date: formatDateForAPI(recommendation.expiration),
        strike_price: recommendation.strike,
        option_type: recommendation.option_type?.toLowerCase() || 'put',
      }

      await axios.post('/api/trades/', tradeData)
      
      if (onSuccess) {
        onSuccess()
      }
      
      // Trigger refresh
      window.dispatchEvent(new Event('tradeAdded'))
      
      if (onClose) {
        onClose()
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create trade')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold mb-4">📝 Create Trade from Recommendation</h3>

        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-50 text-red-800 border border-red-200">
            {error}
          </div>
        )}

        {/* Display recommendation details (read-only) */}
        <div className="mb-4 p-3 bg-slate-50 rounded-md text-sm space-y-1">
          <div><strong>Symbol:</strong> {recommendation.symbol || 'IWM'}</div>
          <div><strong>Type:</strong> {recommendation.option_type?.toUpperCase() || 'PUT'}</div>
          <div><strong>Strike:</strong> ${recommendation.strike?.toFixed(2)}</div>
          <div><strong>Expiration:</strong> {recommendation.expiration || 'N/A'}</div>
          <div><strong>Side:</strong> {getSide(recommendation.action_type).toUpperCase()}</div>
          <div><strong>Bid/Ask:</strong> ${recommendation.bid?.toFixed(2)} / ${recommendation.ask?.toFixed(2)}</div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Quantity (Contracts)
            </label>
            <input
              type="number"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 1 })}
              className="input-field"
              min="1"
              required
            />
            <div className="text-xs text-slate-500 mt-1">
              Recommended: {recommendation.recommended_contracts || 1}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Fill Price (per contract)
            </label>
            <input
              type="number"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0.0 })}
              className="input-field"
              min="0.01"
              step="0.01"
              required
            />
            <div className="text-xs text-slate-500 mt-1">
              Mid: ${recommendation.mid?.toFixed(2)} | 
              Bid: ${recommendation.bid?.toFixed(2)} | 
              Ask: ${recommendation.ask?.toFixed(2)}
            </div>
          </div>

          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 btn-secondary py-2"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 btn-primary py-2 disabled:opacity-50"
            >
              {loading ? 'Creating...' : '✅ Create Trade'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

