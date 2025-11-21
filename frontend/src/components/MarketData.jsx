import { useState, useEffect } from 'react'
import axios from 'axios'

export default function MarketData() {
  const [marketData, setMarketData] = useState(null)
  const [trend, setTrend] = useState(null)
  const [cycleSwing, setCycleSwing] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchMarketData()
    const interval = setInterval(fetchMarketData, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const fetchMarketData = async () => {
    try {
      const [priceRes, trendRes, cycleRes] = await Promise.all([
        axios.get('/api/market-data/iwm-price'),
        axios.get('/api/market-data/indicators/trend'),
        axios.get('/api/market-data/indicators/cycle-swing'),
      ])

      setMarketData(priceRes.data)
      setTrend(trendRes.data)
      setCycleSwing(cycleRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching market data:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="metric-card animate-pulse">
            <div className="h-4 bg-slate-200 rounded w-24 mx-auto mb-2"></div>
            <div className="h-8 bg-slate-200 rounded w-32 mx-auto"></div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">📊 Market Data & Indicators</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* IWM Price */}
        <div className="metric-card">
          <div className="metric-label">IWM Current Price</div>
          <div className="metric-value">
            ${marketData?.price?.toFixed(2) || 'N/A'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {marketData?.delay || '15-20 min delay'}
          </div>
        </div>

        {/* Trend Indicator */}
        <div className={`indicator-card ${trend?.signal_class || ''}`}>
          <div className="metric-label">Ehler's Trend</div>
          <div className="metric-value text-lg">
            {trend?.signal_text || 'NEUTRAL →'}
          </div>
        </div>

        {/* Cycle Swing */}
        <div className={`indicator-card ${cycleSwing?.signal_class || ''}`}>
          <div className="metric-label">Cycle Swing Momentum</div>
          <div className="metric-value text-lg">
            {cycleSwing?.signal_text || 'NEUTRAL'}
          </div>
        </div>
      </div>
    </div>
  )
}

