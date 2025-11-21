import { useState } from 'react'
import axios from 'axios'

export default function TradeForm() {
  const [formData, setFormData] = useState({
    symbol: 'IWM',
    quantity: 1,
    price: 0.80,
    side: 'sell',
    trade_type: 'put',
    strategy: 'wheel',
    expiration_date: '',
    strike_price: 200.0,
  })
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage(null)

    try {
      const tradeData = {
        symbol: formData.symbol.toUpperCase(),
        quantity: formData.quantity,
        price: formData.price,
        side: formData.side,
        strategy: formData.strategy || null,
        expiration_date: formData.trade_type !== 'stock' ? formData.expiration_date : null,
        strike_price: formData.trade_type !== 'stock' ? formData.strike_price : null,
        option_type: formData.trade_type !== 'stock' ? formData.trade_type : null,
      }

      await axios.post('/api/trades/', tradeData)
      setMessage({ type: 'success', text: 'Trade added successfully!' })
      
      // Reset form
      setFormData({
        symbol: 'IWM',
        quantity: 1,
        price: 0.80,
        side: 'sell',
        trade_type: 'put',
        strategy: 'wheel',
        expiration_date: '',
        strike_price: 200.0,
      })
      
      // Trigger refresh in parent
      window.dispatchEvent(new Event('tradeAdded'))
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Error adding trade',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6">
      <h3 className="text-lg font-semibold mb-4">📝 Add New Trade</h3>

      {message && (
        <div
          className={`mb-4 p-3 rounded-md ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Symbol
            </label>
            <input
              type="text"
              value={formData.symbol}
              onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
              className="input-field"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Type
            </label>
            <select
              value={formData.trade_type}
              onChange={(e) => setFormData({ ...formData, trade_type: e.target.value })}
              className="input-field"
            >
              <option value="stock">Stock</option>
              <option value="put">Put</option>
              <option value="call">Call</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Quantity
            </label>
            <input
              type="number"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) })}
              className="input-field"
              min="1"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Side
            </label>
            <select
              value={formData.side}
              onChange={(e) => setFormData({ ...formData, side: e.target.value })}
              className="input-field"
            >
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Price
            </label>
            <input
              type="number"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
              className="input-field"
              min="0.01"
              step="0.01"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Strategy
            </label>
            <input
              type="text"
              value={formData.strategy}
              onChange={(e) => setFormData({ ...formData, strategy: e.target.value })}
              className="input-field"
            />
          </div>
        </div>

        {formData.trade_type !== 'stock' && (
          <>
            <div className="text-sm font-medium text-slate-700 mb-2">
              📋 Contract Details
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Expiration
                </label>
                <input
                  type="date"
                  value={formData.expiration_date}
                  onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
                  className="input-field"
                  required={formData.trade_type !== 'stock'}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Strike
                </label>
                <input
                  type="number"
                  value={formData.strike_price}
                  onChange={(e) => setFormData({ ...formData, strike_price: parseFloat(e.target.value) })}
                  className="input-field"
                  min="0.01"
                  step="0.01"
                  required={formData.trade_type !== 'stock'}
                />
              </div>
            </div>
          </>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full btn-primary py-2 disabled:opacity-50"
        >
          {loading ? 'Adding...' : '➕ Add Trade'}
        </button>
      </form>
    </div>
  )
}

