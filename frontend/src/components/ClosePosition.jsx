import { useState } from 'react'
import axios from 'axios'

export default function ClosePosition({ position, onClose }) {
  const [action, setAction] = useState('')
  const [quantity, setQuantity] = useState(Math.abs(position.net_quantity))
  const [price, setPrice] = useState(0.01)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const isShort = position.net_quantity < 0
  const maxQuantity = Math.abs(position.net_quantity)

  // Determine available actions based on position type
  const availableActions = []
  if (isShort) {
    availableActions.push('Buy to Close')
    availableActions.push('Expire (Worthless)')
    availableActions.push('Assigned/Exercised')
  } else {
    availableActions.push('Sell to Close')
  }

  // Set default action
  if (!action && availableActions.length > 0) {
    setAction(availableActions[0])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      // Determine trade side and price based on action
      let tradeSide = isShort ? 'buy' : 'sell'
      let tradePrice = price

      if (action === 'Expire (Worthless)') {
        tradePrice = 0.0
      } else if (action === 'Assigned/Exercised') {
        // For assignment, we need to create two trades:
        // 1. Stock trade (buying/selling shares at strike price)
        // 2. Option trade (closing out the option position)
        
        // First, create the stock trade
        const stockTrade = {
          symbol: position.symbol,
          quantity: quantity * 100, // 100 shares per contract
          price: position.strike_price,
          side: position.option_type === 'put' ? 'buy' : 'sell',
          strategy: 'assignment',
          expiration_date: null,
          strike_price: null,
          option_type: null,
        }

        await axios.post('/api/trades/', stockTrade)

        // Then, create the option closing trade
        tradePrice = 0.0
        tradeSide = isShort ? 'buy' : 'sell'
      }

      // Parse expiration date if it's a string
      let expirationDate = position.expiration_date
      if (typeof expirationDate === 'string') {
        expirationDate = expirationDate.split('T')[0] // Get just the date part
      }

      const closeTrade = {
        symbol: position.symbol,
        quantity: quantity,
        price: tradePrice,
        side: tradeSide,
        strategy: action === 'Assigned/Exercised' ? 'assignment' : 'close_position',
        expiration_date: expirationDate,
        strike_price: position.strike_price,
        option_type: position.option_type,
      }

      await axios.post('/api/trades/', closeTrade)

      setSuccess(true)
      setTimeout(() => {
        onClose()
        window.dispatchEvent(new Event('tradeAdded'))
      }, 1000)
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to close position'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border-t border-slate-200 pt-4 mt-4">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 text-red-800 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3 text-green-800 text-sm">
            ✅ Position closed successfully!
          </div>
        )}

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Action
            </label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="input-field"
              required
            >
              {availableActions.map((act) => (
                <option key={act} value={act}>
                  {act}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Quantity
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value))}
              className="input-field"
              min="1"
              max={maxQuantity}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Price
            </label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(parseFloat(e.target.value))}
              className="input-field"
              min="0"
              step="0.01"
              required
              disabled={action === 'Expire (Worthless)' || action === 'Assigned/Exercised'}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || success}
          className="w-full btn-primary py-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Processing...' : success ? 'Success!' : 'Execute Trade'}
        </button>
      </form>
    </div>
  )
}

