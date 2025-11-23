import { useState, useEffect } from 'react'
import axios from 'axios'

export default function PortfolioConfig({ onUpdate }) {
  const [startingValue, setStartingValue] = useState(1000000)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const fetchStartingValue = async () => {
    try {
      setError(null)
      const response = await axios.get('/api/config/starting-portfolio-value')
      setStartingValue(response.data.value)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching starting portfolio value:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to fetch starting value'
      setError(errorMessage)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStartingValue()
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      await axios.post('/api/config/starting-portfolio-value', {
        value: startingValue
      })
      setEditing(false)
      if (onUpdate) {
        onUpdate()
      }
      // Trigger refresh of NAV display
      window.dispatchEvent(new Event('tradeAdded'))
    } catch (error) {
      console.error('Error saving starting portfolio value:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to save starting value'
      setError(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    fetchStartingValue()
    setEditing(false)
    setError(null)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <div>Loading configuration...</div>
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

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <label className="text-sm font-medium text-slate-700 block mb-1">
            Starting Portfolio Value
          </label>
          {editing ? (
            <div className="space-y-2">
              <input
                type="number"
                value={startingValue}
                onChange={(e) => setStartingValue(parseFloat(e.target.value) || 0)}
                className="input-field w-full"
                min="1000"
                step="10000"
                disabled={saving}
              />
              {error && (
                <div className="text-sm text-red-600">{error}</div>
              )}
              <div className="flex space-x-2">
                <button
                  onClick={handleSave}
                  disabled={saving || startingValue <= 0}
                  className="btn-primary text-sm"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <span className="text-lg font-semibold text-slate-900">
                {formatCurrency(startingValue)}
              </span>
              <button
                onClick={() => setEditing(true)}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Edit
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

