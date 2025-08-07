import { useState, useEffect } from 'react'
import Header from './components/Header'
import RankingsTable from './components/RankingsTable'
import TierVisualization from './components/TierVisualization'
import PlayerModal from './components/PlayerModal'
import Stats from './components/Stats'

function App() {
  const [selectedPosition, setSelectedPosition] = useState('QB')
  const [selectedScoring, setSelectedScoring] = useState('STD')
  const [selectedPlayer, setSelectedPlayer] = useState(null)
  const [positions, setPositions] = useState([])
  const [apiStats, setApiStats] = useState(null)

  // Fetch available positions and stats on load
  useEffect(() => {
    Promise.all([
      fetch('/api/positions').then(res => res.json()),
      fetch('/api/stats').then(res => res.json())
    ]).then(([positionsData, statsData]) => {
      setPositions(positionsData.positions || [])
      setApiStats(statsData)
    }).catch(err => {
      console.error('Failed to load initial data:', err)
    })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Header 
        apiStats={apiStats}
        positions={positions}
        selectedPosition={selectedPosition}
        selectedScoring={selectedScoring}
        onPositionChange={setSelectedPosition}
        onScoringChange={setSelectedScoring}
      />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Rankings Table - Main Content */}
          <div className="lg:col-span-2">
            <RankingsTable
              position={selectedPosition}
              scoring={selectedScoring}
              onPlayerClick={setSelectedPlayer}
            />
          </div>
          
          {/* Sidebar - Tier Visualization */}
          <div className="lg:col-span-1">
            <TierVisualization
              position={selectedPosition}
              scoring={selectedScoring}
            />
            
            {/* Stats Card */}
            <div className="mt-6">
              <Stats stats={apiStats} />
            </div>
          </div>
        </div>
      </main>

      {/* Player Details Modal */}
      {selectedPlayer && (
        <PlayerModal
          player={selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
        />
      )}
    </div>
  )
}

export default App 