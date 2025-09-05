import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Users, Play, RefreshCw, Loader2, CheckCircle, XCircle, Trash2 } from 'lucide-react'

interface QuickActionsProps {
  onLogUpdate: (updateFn: (prev: string[]) => string[]) => void
  onResultsUpdate?: (results: string) => void
}

const QuickActions: React.FC<QuickActionsProps> = ({ onLogUpdate, onResultsUpdate }) => {
  const [loading, setLoading] = useState<string | null>(null)

  const listClients = async () => {
    setLoading('clients')
    onLogUpdate(prev => ['🔍 Fetching client list...', ...prev.slice(0, 49)])
    
    try {
      onLogUpdate(prev => ['📡 API Call: GET /clients', ...prev.slice(0, 49)])
      const response = await fetch('/clients')
      const data = await response.json()
      
      onLogUpdate(prev => [`📥 Response (${response.status}): ${JSON.stringify(data, null, 2)}`, ...prev.slice(0, 49)])
      
      // Update results display
      if (onResultsUpdate) {
        onResultsUpdate(JSON.stringify(data, null, 2))
      }
      
      if (data.length) {
        onLogUpdate(prev => [`✅ Found ${data.length} configured clients`, ...prev.slice(0, 49)])
      } else {
        onLogUpdate(prev => ['⚠️ No clients configured', ...prev.slice(0, 49)])
      }
    } catch (error) {
      onLogUpdate(prev => [`❌ API Error: ${error}`, ...prev.slice(0, 49)])
    } finally {
      setLoading(null)
    }
  }

  const analyzeAll = async () => {
    setLoading('analyze')
    onLogUpdate(prev => ['🚀 Starting analysis process...', ...prev.slice(0, 49)])
    
    try {
      // First get clients
      const clientsResponse = await fetch('/clients')
      const clients = await clientsResponse.json()
      
      if (!clients.length) {
        onLogUpdate(prev => ['❌ No clients available for analysis', ...prev.slice(0, 49)])
        return
      }
      
      onLogUpdate(prev => [`📋 Found ${clients.length} clients to analyze`, ...prev.slice(0, 49)])
      const clientNames = clients.map((c: any) => c.name)
      
      // Start analysis
      onLogUpdate(prev => ['🔄 Submitting analysis request...', ...prev.slice(0, 49)])
      onLogUpdate(prev => ['📡 API Call: POST /analyze', ...prev.slice(0, 49)])
      
      const response = await fetch('/analyze', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_names: clientNames,
          include_summary: true,
          force_refresh: true
        })
      })
      
      const data = await response.json()
      onLogUpdate(prev => [`📥 Response (${response.status}): ${JSON.stringify(data, null, 2)}`, ...prev.slice(0, 49)])
      
      // Update results display
      if (onResultsUpdate) {
        onResultsUpdate(JSON.stringify(data, null, 2))
      }
      
      if (data.request_id) {
        onLogUpdate(prev => [`✅ Analysis started with ID: ${data.request_id}`, ...prev.slice(0, 49)])
        // Start polling for results
        pollAnalysisResults(data.request_id)
      } else {
        onLogUpdate(prev => ['❌ Analysis failed to start', ...prev.slice(0, 49)])
      }
    } catch (error) {
      onLogUpdate(prev => [`❌ API Error: ${error}`, ...prev.slice(0, 49)])
    } finally {
      setLoading(null)
    }
  }

  const checkHealth = async () => {
    setLoading('health')
    onLogUpdate(prev => ['💚 Checking system health...', ...prev.slice(0, 49)])
    
    try {
      onLogUpdate(prev => ['📡 API Call: GET /health', ...prev.slice(0, 49)])
      const response = await fetch('/health')
      const data = await response.json()
      
      onLogUpdate(prev => [`📥 Response (${response.status}): ${JSON.stringify(data, null, 2)}`, ...prev.slice(0, 49)])
      
      const uptimeSeconds = Math.round(data.uptime || 0)
      const message = `✅ Health: ${data.status}, Clients: ${data.connected_clients}, Uptime: ${uptimeSeconds}s`
      onLogUpdate(prev => [message, ...prev.slice(0, 49)])
    } catch (error) {
      onLogUpdate(prev => [`❌ Health check failed: ${error}`, ...prev.slice(0, 49)])
    } finally {
      setLoading(null)
    }
  }

  const clearLogs = () => {
    onLogUpdate(() => ['🗑️ Logs cleared'])
  }

  const pollAnalysisResults = async (requestId: string) => {
    onLogUpdate(prev => [`🔄 Checking analysis progress for ${requestId}...`, ...prev.slice(0, 49)])
    
    try {
      const response = await fetch(`/analyze/${requestId}`)
      const result = await response.json()
      
      if (result.status === 'completed') {
        onLogUpdate(prev => [`✅ Analysis completed for ${requestId}!`, ...prev.slice(0, 49)])
        
        // Update results display with the complete analysis
        if (onResultsUpdate) {
          onResultsUpdate(JSON.stringify(result, null, 2))
        }
        
        // Show summary if available
        if (result.summary) {
          onLogUpdate(prev => [`📊 Summary: ${result.summary}`, ...prev.slice(0, 49)])
        }
        
        // Show log analysis results
        if (result.analysis && result.analysis.logs) {
          onLogUpdate(prev => [`📋 Log files analyzed: ${result.analysis.logs.length}`, ...prev.slice(0, 49)])
        }
        
      } else if (result.status === 'failed') {
        onLogUpdate(prev => [`❌ Analysis failed for ${requestId}: ${result.error || 'Unknown error'}`, ...prev.slice(0, 49)])
        if (onResultsUpdate) {
          onResultsUpdate(JSON.stringify(result, null, 2))
        }
      } else if (result.status === 'not_found') {
        onLogUpdate(prev => [`❌ Analysis ${requestId} not found`, ...prev.slice(0, 49)])
      } else {
        // Still running, poll again
        const status = result.status || 'unknown'
        onLogUpdate(prev => [`⏳ Analysis still running... Status: ${status}`, ...prev.slice(0, 49)])
        setTimeout(() => pollAnalysisResults(requestId), 2000)
      }
    } catch (error) {
      onLogUpdate(prev => [`❌ Polling error: ${error}`, ...prev.slice(0, 49)])
    }
  }

  const actions = [
    {
      id: 'clients',
      label: 'List Clients',
      description: 'Show connected log sources',
      icon: Users,
      color: 'primary',
      onClick: listClients
    },
    {
      id: 'analyze',
      label: 'Analyze All',
      description: 'Start log analysis process',
      icon: Play,
      color: 'success',
      onClick: analyzeAll
    },
    {
      id: 'health',
      label: 'System Health',
      description: 'Check system status',
      icon: RefreshCw,
      color: 'warning',
      onClick: checkHealth
    },
    {
      id: 'clear',
      label: 'Clear Logs',
      description: 'Clear log display',
      icon: Trash2,
      color: 'error',
      onClick: clearLogs
    }
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-2 h-6 bg-gradient-to-b from-primary-400 to-primary-600 rounded-full"></div>
        <h3 className="text-lg font-semibold text-white">Quick Actions</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {actions.map((action, index) => (
          <motion.button
            key={action.id}
            onClick={action.onClick}
            disabled={loading === action.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.02, x: 4 }}
            whileTap={{ scale: 0.98 }}
            className={`w-full p-4 rounded-xl backdrop-blur-sm border transition-all duration-200 ${
              loading === action.id 
                ? 'bg-dark-400/20 border-dark-400/30 cursor-not-allowed' 
                : action.color === 'primary' 
                  ? 'bg-primary-500/10 border-primary-500/30 hover:bg-primary-500/20 hover:border-primary-500/50'
                  : action.color === 'success'
                    ? 'bg-success-500/10 border-success-500/30 hover:bg-success-500/20 hover:border-success-500/50'
                    : action.color === 'warning'
                      ? 'bg-warning-500/10 border-warning-500/30 hover:bg-warning-500/20 hover:border-warning-500/50'
                      : 'bg-error-500/10 border-error-500/30 hover:bg-error-500/20 hover:border-error-500/50'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${
                loading === action.id 
                  ? 'bg-dark-400/20' 
                  : action.color === 'primary' 
                    ? 'bg-primary-500/20'
                    : action.color === 'success'
                      ? 'bg-success-500/20'
                      : action.color === 'warning'
                        ? 'bg-warning-500/20'
                        : 'bg-error-500/20'
              }`}>
                {loading === action.id ? (
                  <Loader2 className="w-5 h-5 text-dark-600 animate-spin" />
                ) : (
                  <action.icon className={`w-5 h-5 ${
                    action.color === 'primary' ? 'text-primary-400' :
                    action.color === 'success' ? 'text-success-400' :
                    action.color === 'warning' ? 'text-warning-400' : 'text-error-400'
                  }`} />
                )}
              </div>
              <div className="text-left flex-1">
                <div className="font-medium text-white">{action.label}</div>
                <div className="text-sm text-dark-600">{action.description}</div>
              </div>
            </div>
          </motion.button>
        ))}
      </div>

      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-6 p-4 rounded-xl bg-primary-500/10 border border-primary-400/30"
      >
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle className="w-4 h-4 text-primary-400" />
          <span className="text-sm font-medium text-primary-300">Tips</span>
        </div>
        <ul className="text-xs text-dark-600 space-y-1">
          <li>• Use "List Clients" to verify connections</li>
          <li>• "Analyze All" processes all available logs</li>
          <li>• Check system health regularly</li>
        </ul>
      </motion.div>
    </div>
  )
}

export default QuickActions