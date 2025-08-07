import { useState, useEffect } from 'react'

const RankingsTable = ({ position, scoring, onPlayerClick }) => {
  const [rankings, setRankings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch rankings when position or scoring changes
  useEffect(() => {
    const fetchRankings = async () => {
      if (!position) return
      
      setLoading(true)
      setError(null)
      
      try {
        const response = await fetch(`/api/rankings/${position}?week=0&scoring=${scoring}&limit=100`)
        if (!response.ok) throw new Error('Failed to fetch rankings')
        
        const data = await response.json()
        setRankings(data.players || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchRankings()
  }, [position, scoring])

  // Generate tier based on rank_std
  const getTier = (rankStd, rank) => {
    if (!rankStd) return null
    
    // Simple tier logic based on standard deviation
    if (rankStd <= 0.5) return 1 // Very consistent
    if (rankStd <= 1.0) return 2 // Consistent
    if (rankStd <= 1.5) return 3 // Some disagreement
    if (rankStd <= 2.0) return 4 // High disagreement
    return 5 // Very high disagreement
  }

  const getTierClass = (tier) => {
    if (!tier) return ''
    return `tier-${tier} border-l-4`
  }

  const getPositionClass = (pos) => {
    return `position-${pos.toLowerCase()}`
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="text-center">
          <div className="text-red-500 text-lg font-medium">Failed to load rankings</div>
          <div className="text-gray-500 mt-2">{error}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {position} Rankings - {scoring === 'STD' ? 'Standard' : scoring === 'PPR' ? 'PPR' : 'Half PPR'}
          </h2>
          <div className="text-sm text-gray-500">
            {rankings.length} players
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden">
        <div className="max-h-96 overflow-y-auto custom-scrollbar">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rank
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Player
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Team
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Range
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Consensus
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tier
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rankings.map((player, index) => {
                const tier = getTier(player.rank_std, player.rank)
                return (
                  <tr
                    key={`${player.player_name}-${index}`}
                    className={`table-row ${getTierClass(tier)}`}
                    onClick={() => onPlayerClick(player)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <span className="text-2xl font-bold text-gray-900">
                          {player.rank}
                        </span>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {player.player_name}
                          </div>
                          <div className={`text-xs px-2 py-1 rounded-full inline-block ${getPositionClass(player.position)}`}>
                            {player.position}
                          </div>
                        </div>
                      </div>
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {player.team}
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {player.rank_min && player.rank_max ? (
                        <span>{player.rank_min}-{player.rank_max}</span>
                      ) : '-'}
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {player.rank_avg ? player.rank_avg.toFixed(1) : '-'}
                    </td>
                    
                    <td className="px-6 py-4 whitespace-nowrap">
                      {tier && (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium tier-${tier}`}>
                          Tier {tier}
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

      {rankings.length === 0 && !loading && (
        <div className="px-6 py-8 text-center text-gray-500">
          No rankings available for {position} {scoring}
        </div>
      )}
    </div>
  )
}

export default RankingsTable 