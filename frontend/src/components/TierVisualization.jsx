import { useState, useEffect } from 'react'

const TierVisualization = ({ position, scoring }) => {
  const [rankings, setRankings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchRankings = async () => {
      if (!position) return
      
      setLoading(true)
      try {
        let combinedRankings = []
        
        if (position === 'Overall') {
          // Fetch all positions and combine them
          const positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
          const promises = positions.map(pos => 
            fetch(`/api/rankings/${pos}?week=0&scoring=${scoring}&limit=100`)
              .then(res => res.ok ? res.json() : { players: [] })
              .catch(() => ({ players: [] }))
          )
          
          const results = await Promise.all(promises)
          combinedRankings = results.flatMap(result => result.players || [])
          
        } else if (position === 'FLEX') {
          // FLEX includes RB, WR, TE only
          const flexPositions = ['RB', 'WR', 'TE']
          const promises = flexPositions.map(pos => 
            fetch(`/api/rankings/${pos}?week=0&scoring=${scoring}&limit=100`)
              .then(res => res.ok ? res.json() : { players: [] })
              .catch(() => ({ players: [] }))
          )
          
          const results = await Promise.all(promises)
          combinedRankings = results.flatMap(result => result.players || [])
          
        } else {
          // Regular position
          const response = await fetch(`/api/rankings/${position}?week=0&scoring=${scoring}&limit=100`)
          if (response.ok) {
            const data = await response.json()
            combinedRankings = data.players || []
          }
        }
        
        setRankings(combinedRankings)
        
      } catch (err) {
        console.error('Failed to fetch tier data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchRankings()
  }, [position, scoring])

  // Generate tier based on rank_std - SAME logic as RankingsTable
  const getTier = (rankStd) => {
    if (!rankStd) return null
    // Realistic tier logic for fantasy football data
    if (rankStd <= 2.0) return 1 // Elite consensus (very low disagreement)
    if (rankStd <= 4.0) return 2 // Solid consensus (low disagreement)
    if (rankStd <= 6.0) return 3 // Decent consensus (moderate disagreement)
    if (rankStd <= 10.0) return 4 // Risky consensus (high disagreement)
    return 5 // Volatile (very high disagreement)
  }

  // Calculate tier distribution
  const tierDistribution = rankings.reduce((acc, player) => {
    const tier = getTier(player.rank_std)
    if (tier) {
      acc[tier] = (acc[tier] || 0) + 1
    }
    return acc
  }, {})

  const totalPlayers = Object.values(tierDistribution).reduce((sum, count) => sum + count, 0)

  const tierInfo = {
    1: { name: 'Elite', color: 'bg-green-500', desc: 'Very low disagreement (≤2.0)' },
    2: { name: 'Solid', color: 'bg-blue-500', desc: 'Low disagreement (2.0-4.0)' },
    3: { name: 'Decent', color: 'bg-yellow-500', desc: 'Moderate disagreement (4.0-6.0)' },
    4: { name: 'Risky', color: 'bg-orange-500', desc: 'High disagreement (6.0-10.0)' },
    5: { name: 'Volatile', color: 'bg-red-500', desc: 'Very high disagreement (>10.0)' }
  }

  // Calculate average standard deviation for insights
  const avgStdDev = rankings.length > 0 
    ? rankings.reduce((sum, p) => sum + (p.rank_std || 0), 0) / rankings.length
    : 0

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Tier Breakdown */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Tier Breakdown</h3>
          <p className="text-sm text-gray-500 mt-1">
            Based on expert consensus variation
          </p>
        </div>

        <div className="p-6 space-y-4">
          {[1, 2, 3, 4, 5].map(tier => {
            const count = tierDistribution[tier] || 0
            const percentage = totalPlayers > 0 ? (count / totalPlayers * 100) : 0
            const info = tierInfo[tier]

            return (
              <div key={tier} className="flex items-center space-x-3">
                <div className="flex-shrink-0 w-12 text-sm font-medium text-gray-600">
                  Tier {tier}
                </div>
                
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900">
                      {info.name}
                    </span>
                    <span className="text-sm text-gray-500">
                      {count} players ({percentage.toFixed(0)}%)
                    </span>
                  </div>
                  
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${info.color}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  
                  <div className="text-xs text-gray-500 mt-1">
                    {info.desc}
                  </div>
                </div>
              </div>
            )
          })}

          {totalPlayers === 0 && (
            <div className="text-center py-8 text-gray-500">
              No tier data available
            </div>
          )}
        </div>
      </div>

      {/* Consensus Insights */}
      {totalPlayers > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Consensus Insights</h3>
          </div>
          
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {avgStdDev.toFixed(1)}
                </div>
                <div className="text-xs text-blue-600 font-medium">Avg Std Dev</div>
              </div>
              
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {(tierDistribution[1] || 0) + (tierDistribution[2] || 0)}
                </div>
                <div className="text-xs text-green-600 font-medium">Safe Picks</div>
                <div className="text-xs text-gray-500">Tiers 1-2</div>
              </div>
            </div>

            <div className="text-xs text-gray-600 space-y-1">
              <div><strong>Interpretation:</strong></div>
              <div>• <strong>Lower std dev</strong> = Higher expert consensus = Safer pick</div>
              <div>• <strong>Higher std dev</strong> = More expert disagreement = Riskier pick</div>
              <div>• Players in Tiers 1-2 have the most expert agreement</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TierVisualization 