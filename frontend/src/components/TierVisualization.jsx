import { useState, useEffect } from 'react'

const TierVisualization = ({ position, scoring }) => {
  const [rankings, setRankings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchRankings = async () => {
      if (!position) return
      
      setLoading(true)
      try {
        const response = await fetch(`/api/rankings/${position}?week=0&scoring=${scoring}&limit=100`)
        if (response.ok) {
          const data = await response.json()
          setRankings(data.players || [])
        }
      } catch (err) {
        console.error('Failed to fetch tier data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchRankings()
  }, [position, scoring])

  // Generate tier based on rank_std
  const getTier = (rankStd) => {
    if (!rankStd) return null
    if (rankStd <= 0.5) return 1
    if (rankStd <= 1.0) return 2
    if (rankStd <= 1.5) return 3
    if (rankStd <= 2.0) return 4
    return 5
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
    1: { name: 'Elite', color: 'bg-green-500', desc: 'High expert consensus' },
    2: { name: 'Solid', color: 'bg-blue-500', desc: 'Good consensus' },
    3: { name: 'Decent', color: 'bg-yellow-500', desc: 'Some disagreement' },
    4: { name: 'Risky', color: 'bg-orange-500', desc: 'High disagreement' },
    5: { name: 'Volatile', color: 'bg-red-500', desc: 'Very high disagreement' }
  }

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
                    {count} players
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

      {/* Tier Legend */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <div className="text-xs text-gray-600">
          <div className="font-medium mb-2">How Tiers Work:</div>
          <div className="space-y-1">
            <div>• <strong>Lower standard deviation</strong> = Higher expert consensus</div>
            <div>• <strong>Higher standard deviation</strong> = More expert disagreement</div>
            <div>• Players in higher tiers are considered more reliable picks</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TierVisualization 