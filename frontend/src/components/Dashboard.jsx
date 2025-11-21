import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import MarketData from './MarketData'
import PerformanceMetrics from './PerformanceMetrics'
import TradeHistory from './TradeHistory'
import TradeForm from './TradeForm'
import Recommendations from './Recommendations'
import Analytics from './Analytics'
import CostBasis from './CostBasis'
import OpenPositions from './OpenPositions'

export default function Dashboard() {
  const { username, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [accountSize, setAccountSize] = useState(1000000)

  const handleLogout = async () => {
    await logout()
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">
                🎯 IWM Put Selling Strategy Tracker
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-slate-600">Welcome, {username}</span>
              <button
                onClick={handleLogout}
                className="btn-secondary text-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'dashboard', label: 'Dashboard' },
              { id: 'trades', label: 'Trades' },
              { id: 'recommendations', label: 'Recommendations' },
              { id: 'analytics', label: 'Analytics' },
              { id: 'cost-basis', label: 'Cost Basis' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <div className="flex justify-end items-center space-x-4 mb-4">
              <label className="text-sm font-medium text-slate-700">
                Account Size ($):
              </label>
              <input
                type="number"
                value={accountSize}
                onChange={(e) => setAccountSize(parseFloat(e.target.value))}
                className="input-field w-40"
                min="1000"
                step="10000"
              />
            </div>
            <MarketData />
            <PerformanceMetrics accountSize={accountSize} />
            <OpenPositions />
          </div>
        )}

        {activeTab === 'trades' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <TradeForm />
            </div>
            <div className="lg:col-span-2">
              <TradeHistory />
            </div>
          </div>
        )}

        {activeTab === 'recommendations' && (
          <Recommendations accountSize={accountSize} />
        )}

        {activeTab === 'analytics' && <Analytics />}

        {activeTab === 'cost-basis' && <CostBasis />}
      </main>
    </div>
  )
}

