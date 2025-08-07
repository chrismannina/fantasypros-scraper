import { useState, useEffect } from 'react'

const PlayerModal = ({ player, onClose }) => {
  const [playerData, setPlayerData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPlayerData = async () => {
      if (!player?.player_name) return
      
      setLoading(true)
      try {
        const encodedName = encodeURIComponent(player.player_name)
        const response = await fetch(`/api/players/${encodedName}`)
        if (response.ok) {
          const data = await response.json()
          setPlayerData(data)
        }
      } catch (err) {
        console.error('Failed to fetch player data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchPlayerData()
  }, [player])

  // SAME tier logic as other components
  const getTier = (rankStd) => {
    if (!rankStd) return null
    // Realistic tier logic for fantasy football data
    if (rankStd <= 2.0) return { tier: 1, name: 'Elite' }
    if (rankStd <= 4.0) return { tier: 2, name: 'Solid' }
    if (rankStd <= 6.0) return { tier: 3, name: 'Decent' }
    if (rankStd <= 10.0) return { tier: 4, name: 'Risky' }
    return { tier: 5, name: 'Volatile' }
  }

  const getPositionColor = (pos) => {
    const colors = {
      QB: 'bg-purple-100 text-purple-800 border-purple-200',
      RB: 'bg-green-100 text-green-800 border-green-200',
      WR: 'bg-blue-100 text-blue-800 border-blue-200',
      TE: 'bg-orange-100 text-orange-800 border-orange-200',
      K: 'bg-gray-100 text-gray-800 border-gray-200',
      DST: 'bg-red-100 text-red-800 border-red-200'
    }
    return colors[pos] || 'bg-gray-100 text-gray-800 border-gray-200'
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleDateString()
  }

  // Handle backdrop click
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // Get tier description
  const getTierDescription = (tier) => {
    const descriptions = {
      1: "Elite consensus - experts strongly agree, very safe pick",
      2: "Solid consensus - good expert agreement, safe pick", 
      3: "Decent consensus - moderate expert agreement",
      4: "Risky consensus - significant expert disagreement",
      5: "Volatile consensus - experts widely disagree, high risk/reward"
    }
    return descriptions[tier] || "Unknown consensus level"
  }

  if (!player) return null

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-96 overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-gray-900">{player.player_name}</h2>
            <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getPositionColor(player.position)}`}>
              {player.position}
            </span>
            <span className="text-lg font-semibold text-gray-600">{player.team}</span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Current Ranking Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Current Ranking</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Expert Consensus:</span>
                      <span className="font-semibold">#{player.rank}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Expert Range:</span>
                      <span className="font-semibold">#{player.rank_min} - #{player.rank_max}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Average Rank:</span>
                      <span className="font-semibold">{player.rank_avg?.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Standard Deviation:</span>
                      <span className="font-semibold">{player.rank_std?.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Tier Analysis</h3>
                  {(() => {
                    const tierInfo = getTier(player.rank_std)
                    return tierInfo ? (
                      <div className="space-y-2">
                        <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium tier-${tierInfo.tier}`}>
                          Tier {tierInfo.tier} - {tierInfo.name}
                        </div>
                        <div className="text-sm text-gray-600">
                          {getTierDescription(tierInfo.tier)}
                        </div>
                        <div className="text-xs text-gray-500">
                          Std Dev: {player.rank_std?.toFixed(2)} ({tierInfo.tier <= 2 ? 'Low' : tierInfo.tier <= 4 ? 'Medium' : 'High'} disagreement)
                        </div>
                      </div>
                    ) : (
                      <div className="text-gray-500">No tier data available</div>
                    )
                  })()}
                </div>
              </div>

              {/* Cross-Format Comparison */}
              {playerData && playerData.rankings && Object.keys(playerData.rankings).length > 1 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-3">Cross-Format Comparison</h3>
                  <div className="bg-gray-50 rounded-lg overflow-hidden">
                    <table className="min-w-full">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Format</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Std Dev</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tier</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {Object.entries(playerData.rankings).map(([key, ranking]) => {
                          const tierInfo = getTier(ranking.rank_std)
                          return (
                            <tr key={key}>
                              <td className="px-4 py-2 text-sm font-medium text-gray-900">
                                {ranking.scoring}
                              </td>
                              <td className="px-4 py-2 text-sm text-gray-600">
                                #{ranking.rank}
                              </td>
                              <td className="px-4 py-2 text-sm text-gray-600">
                                {ranking.rank_std?.toFixed(2)}
                              </td>
                              <td className="px-4 py-2 text-sm">
                                {tierInfo && (
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium tier-${tierInfo.tier}`}>
                                    {tierInfo.tier}
                                  </span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Last Updated */}
              <div className="text-xs text-gray-500 pt-2 border-t border-gray-200">
                Last updated: {formatDate(player.scraped_at)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PlayerModal 