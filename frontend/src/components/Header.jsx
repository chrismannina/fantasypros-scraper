const Header = ({ 
  apiStats, 
  positions, 
  selectedPosition, 
  selectedScoring, 
  onPositionChange, 
  onScoringChange 
}) => {
  const scoringOptions = [
    { value: 'STD', label: 'Standard', desc: 'Standard scoring' },
    { value: 'PPR', label: 'PPR', desc: 'Point per reception' },
    { value: 'HALF', label: 'Half PPR', desc: '0.5 point per reception' }
  ]

  const scoringDependentPositions = ['RB', 'WR', 'TE']
  const showScoringSelector = scoringDependentPositions.includes(selectedPosition)

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Title */}
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-gray-900">
              🏈 <span className="text-fantasy-blue">FantasyPros</span> Analytics
            </h1>
            {apiStats && (
              <div className="ml-4 text-sm text-gray-500">
                {apiStats.players.toLocaleString()} players • {apiStats.rankings.toLocaleString()} rankings
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center space-x-6">
            {/* Position Selector */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Position:</label>
              <select
                value={selectedPosition}
                onChange={(e) => onPositionChange(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-fantasy-blue focus:border-fantasy-blue"
              >
                {positions.map(position => (
                  <option key={position} value={position}>
                    {position}
                  </option>
                ))}
              </select>
            </div>

            {/* Scoring Selector - Only for RB, WR, TE */}
            {showScoringSelector && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Scoring:</label>
                <div className="flex bg-gray-100 rounded-lg p-1">
                  {scoringOptions.map(option => (
                    <button
                      key={option.value}
                      onClick={() => onScoringChange(option.value)}
                      className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                        selectedScoring === option.value
                          ? 'bg-white text-fantasy-blue shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                      title={option.desc}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Success Rate Badge */}
            {apiStats && (
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-1 bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs font-medium">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span>{apiStats.success_rate_24h}% success</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header 