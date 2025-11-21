import { useState } from 'react'
import { useDatabase } from '../contexts/DatabaseContext'

export default function DatabaseSwitcher() {
  const { dbMode, switchDatabase, isProduction } = useDatabase()
  const [showConfirm, setShowConfirm] = useState(false)

  const handleSwitch = () => {
    setShowConfirm(true)
  }

  const confirmSwitch = () => {
    const newMode = dbMode === 'prod' ? 'test' : 'prod'
    switchDatabase(newMode)
    setShowConfirm(false)
    // Reload the page to refresh all data
    window.location.reload()
  }

  const cancelSwitch = () => {
    setShowConfirm(false)
  }

  return (
    <div className="relative">
      <button
        onClick={handleSwitch}
        className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          isProduction
            ? 'bg-green-100 text-green-800 hover:bg-green-200'
            : 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
        }`}
        title={`Current: ${isProduction ? 'Production' : 'Test'} Database`}
      >
        {isProduction ? '📊 PROD' : '🧪 TEST'}
      </button>

      {showConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">
              Switch Database?
            </h3>
            <p className="text-slate-600 mb-4">
              You are about to switch from{' '}
              <strong>{isProduction ? 'Production' : 'Test'}</strong> to{' '}
              <strong>{isProduction ? 'Test' : 'Production'}</strong> database.
            </p>
            <p className="text-sm text-slate-500 mb-6">
              This will reload the page and all data will be refreshed from the selected database.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={cancelSwitch}
                className="flex-1 btn-secondary py-2"
              >
                Cancel
              </button>
              <button
                onClick={confirmSwitch}
                className={`flex-1 py-2 rounded-md font-medium ${
                  isProduction
                    ? 'bg-yellow-500 text-white hover:bg-yellow-600'
                    : 'bg-green-500 text-white hover:bg-green-600'
                }`}
              >
                Switch to {isProduction ? 'Test' : 'Production'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

