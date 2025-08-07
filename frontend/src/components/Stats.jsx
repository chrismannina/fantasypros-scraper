const Stats = ({ stats }) => {
  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-6 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const formatLastUpdate = (dateString) => {
    if (!dateString) return 'Unknown'
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    
    if (diffHours >= 24) {
      return `${Math.floor(diffHours / 24)} day${Math.floor(diffHours / 24) !== 1 ? 's' : ''} ago`
    } else if (diffHours >= 1) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
    } else if (diffMinutes >= 1) {
      return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`
    } else {
      return 'Just now'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">System Stats</h3>
      </div>

      <div className="p-6 space-y-4">
        {/* Data Overview */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Data Overview</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {stats.players?.toLocaleString() || '0'}
              </div>
              <div className="text-xs text-blue-600 font-medium">Players</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {stats.rankings?.toLocaleString() || '0'}
              </div>
              <div className="text-xs text-green-600 font-medium">Rankings</div>
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Data Quality</h4>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-sm text-gray-600">24h Success Rate</span>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${
                stats.success_rate_24h >= 95 ? 'bg-green-400' :
                stats.success_rate_24h >= 85 ? 'bg-yellow-400' : 'bg-red-400'
              }`}></div>
              <span className="font-semibold text-gray-900">
                {stats.success_rate_24h || 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Last Update */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Freshness</h4>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-sm text-gray-600">Last Update</span>
            <span className="text-sm font-medium text-gray-900">
              {stats.last_updated ? formatLastUpdate(stats.last_updated) : 'Unknown'}
            </span>
          </div>
        </div>

        {/* System Health */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">System Health</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Database</span>
              <span className="inline-flex items-center text-xs">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-1"></div>
                Healthy
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">API</span>
              <span className="inline-flex items-center text-xs">
                <div className="w-2 h-2 bg-green-400 rounded-full mr-1"></div>
                Operational
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">Scraper</span>
              <span className="inline-flex items-center text-xs">
                <div className={`w-2 h-2 rounded-full mr-1 ${
                  stats.success_rate_24h >= 90 ? 'bg-green-400' : 'bg-yellow-400'
                }`}></div>
                {stats.success_rate_24h >= 90 ? 'Active' : 'Limited'}
              </span>
            </div>
          </div>
        </div>

        {/* Version */}
        <div className="pt-2 border-t border-gray-200">
          <div className="text-xs text-gray-500 text-center">
            FantasyPros Analytics v1.0
            <br />
            Hobby-grade fantasy football insights
          </div>
        </div>
      </div>
    </div>
  )
}

export default Stats 