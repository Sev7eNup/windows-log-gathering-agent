import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, Play, Loader2, Computer, CheckCircle } from 'lucide-react'

interface Client {
  name: string
  hostname: string
  ip: string
}

interface ClientSelectorProps {
  onLogUpdate: (updateFn: (prev: string[]) => string[]) => void
  onResultsUpdate?: (results: string) => void
}

const ClientSelector: React.FC<ClientSelectorProps> = ({ onLogUpdate, onResultsUpdate }) => {
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClient, setSelectedClient] = useState<string>('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingClients, setLoadingClients] = useState(false)

  const fetchClients = async () => {
    setLoadingClients(true)
    try {
      const response = await fetch('/clients')
      const data = await response.json()
      setClients(data)
      if (data.length > 0 && !selectedClient) {
        setSelectedClient(data[0].name)
      }
    } catch (error) {
      console.error('Failed to fetch clients:', error)
      onLogUpdate(prev => [`❌ Failed to load clients: ${error}`, ...prev.slice(0, 49)])
    } finally {
      setLoadingClients(false)
    }
  }

  useEffect(() => {
    fetchClients()
  }, [])

  const analyzeSelectedClient = async () => {
    if (!selectedClient) {
      onLogUpdate(prev => ['❌ No client selected', ...prev.slice(0, 49)])
      return
    }

    setLoading(true)
    onLogUpdate(prev => [`🚀 Starting analysis for ${selectedClient}...`, ...prev.slice(0, 49)])

    try {
      onLogUpdate(prev => [`📡 API Call: POST /analyze for ${selectedClient}`, ...prev.slice(0, 49)])
      
      const response = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_names: [selectedClient],
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
        onLogUpdate(prev => [`✅ Analysis started for ${selectedClient} with ID: ${data.request_id}`, ...prev.slice(0, 49)])
        // Start polling for results
        pollAnalysisResults(data.request_id)
      } else {
        onLogUpdate(prev => [`❌ Analysis failed to start for ${selectedClient}`, ...prev.slice(0, 49)])
      }
    } catch (error) {
      onLogUpdate(prev => [`❌ API Error for ${selectedClient}: ${error}`, ...prev.slice(0, 49)])
    } finally {
      setLoading(false)
    }
  }

  const pollAnalysisResults = async (requestId: string) => {
    onLogUpdate(prev => [`🔄 Checking analysis progress for ${requestId}...`, ...prev.slice(0, 49)])
    
    try {
      const response = await fetch(`/analyze/${requestId}`)
      const result = await response.json()
      
      if (result.status === 'completed') {
        onLogUpdate(prev => [`✅ Analysis completed for ${selectedClient}!`, ...prev.slice(0, 49)])
        
        // Update results display with the complete analysis
        if (onResultsUpdate) {
          onResultsUpdate(JSON.stringify(result, null, 2))
        }
        
        // Show summary if available
        if (result.summary) {
          onLogUpdate(prev => [`📊 Summary for ${selectedClient}: ${result.summary}`, ...prev.slice(0, 49)])
        }
        
        // Show log analysis results
        if (result.analysis && result.analysis.logs) {
          onLogUpdate(prev => [`📋 Log files analyzed for ${selectedClient}: ${result.analysis.logs.length}`, ...prev.slice(0, 49)])
        }
        
      } else if (result.status === 'failed') {
        onLogUpdate(prev => [`❌ Analysis failed for ${selectedClient}: ${result.error || 'Unknown error'}`, ...prev.slice(0, 49)])
        if (onResultsUpdate) {
          onResultsUpdate(JSON.stringify(result, null, 2))
        }
      } else if (result.status === 'not_found') {
        onLogUpdate(prev => [`❌ Analysis ${requestId} not found`, ...prev.slice(0, 49)])
      } else {
        // Still running, poll again
        const status = result.status || 'unknown'
        onLogUpdate(prev => [`⏳ Analysis still running for ${selectedClient}... Status: ${status}`, ...prev.slice(0, 49)])
        setTimeout(() => pollAnalysisResults(requestId), 2000)
      }
    } catch (error) {
      onLogUpdate(prev => [`❌ Polling error for ${selectedClient}: ${error}`, ...prev.slice(0, 49)])
    }
  }

  const getSelectedClientInfo = () => {
    return clients.find(client => client.name === selectedClient)
  }

  const selectedClientInfo = getSelectedClientInfo()

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-2 h-6 bg-gradient-to-b from-success-400 to-success-600 rounded-full"></div>
        <h3 className="text-lg font-semibold text-white">Client Analysis</h3>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-end">
        {/* Client Selector */}
        <div className="flex-1 min-w-0">
          <label className="block text-sm font-medium text-dark-600 mb-2">
            Select Client for Analysis
          </label>
          <div className="relative">
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              disabled={loadingClients}
              className="w-full flex items-center justify-between px-4 py-3 bg-dark-300/20 border border-dark-400/30 rounded-lg text-white hover:bg-dark-300/30 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-success-400/50"
            >
              <div className="flex items-center gap-3">
                <Computer className="w-4 h-4 text-success-400" />
                <div className="text-left">
                  {loadingClients ? (
                    <span className="text-dark-600">Loading clients...</span>
                  ) : selectedClient ? (
                    <>
                      <div className="font-medium">{selectedClient}</div>
                      {selectedClientInfo && (
                        <div className="text-xs text-dark-600">
                          {selectedClientInfo.hostname} ({selectedClientInfo.ip})
                        </div>
                      )}
                    </>
                  ) : (
                    <span className="text-dark-600">Select a client</span>
                  )}
                </div>
              </div>
              {loadingClients ? (
                <Loader2 className="w-4 h-4 animate-spin text-dark-600" />
              ) : (
                <ChevronDown className={`w-4 h-4 text-dark-600 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
              )}
            </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && !loadingClients && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="absolute top-full left-0 right-0 mt-1 bg-dark-200 border border-dark-400/30 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto"
              >
                {clients.map((client) => (
                  <button
                    key={client.name}
                    onClick={() => {
                      setSelectedClient(client.name)
                      setIsDropdownOpen(false)
                    }}
                    className="w-full px-4 py-3 text-left hover:bg-dark-300/30 transition-all duration-200 flex items-center justify-between group"
                  >
                    <div className="flex items-center gap-3">
                      <Computer className="w-4 h-4 text-success-400" />
                      <div>
                        <div className="font-medium text-white">{client.name}</div>
                        <div className="text-xs text-dark-600">
                          {client.hostname} ({client.ip})
                        </div>
                      </div>
                    </div>
                    {selectedClient === client.name && (
                      <CheckCircle className="w-4 h-4 text-success-400" />
                    )}
                  </button>
                ))}
              </motion.div>
            )}
          </div>
        </div>

        {/* Analyze Button */}
        <motion.button
          onClick={analyzeSelectedClient}
          disabled={loading || !selectedClient || loadingClients}
          whileHover={{ scale: loading ? 1 : 1.02 }}
          whileTap={{ scale: loading ? 1 : 0.98 }}
          className={`px-6 py-3 h-[64px] rounded-lg font-medium transition-all duration-200 flex items-center gap-2 ${
            loading || !selectedClient || loadingClients
              ? 'bg-dark-400/20 text-dark-600 cursor-not-allowed'
              : 'bg-success-500/20 text-white border border-success-400/30 hover:bg-success-500/30 hover:border-success-400/50'
          }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Analyze Client
            </>
          )}
        </motion.button>
      </div>

      {/* Client Info Display */}
      {selectedClientInfo && !loadingClients && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-lg bg-success-500/10 border border-success-400/30"
        >
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-success-400" />
            <span className="text-sm font-medium text-white">Selected Client</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div>
              <p className="text-dark-600">Target Machine</p>
              <p className="font-medium text-white">{selectedClientInfo.name}</p>
            </div>
            <div>
              <p className="text-dark-600">Connection Type</p>
              <p className="font-medium text-white">
                {selectedClientInfo.hostname === 'localhost' || selectedClientInfo.ip === '127.0.0.1' 
                  ? 'Direct Local' 
                  : 'SMB + WinRM'}
              </p>
            </div>
            <div>
              <p className="text-dark-600">Network Address</p>
              <p className="font-medium text-white">{selectedClientInfo.hostname}</p>
            </div>
            <div>
              <p className="text-dark-600">Status</p>
              <p className="font-medium text-success-400">Ready for Analysis</p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default ClientSelector