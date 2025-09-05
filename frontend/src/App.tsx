import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Server, MessageSquare, Settings, AlertCircle } from 'lucide-react'
import QuickActions from './components/QuickActions'
import ClientSelector from './components/ClientSelector'
import ChatInterface from './components/ChatInterface'
import SystemStatus from './components/SystemStatus'
import LogViewer from './components/LogViewer'
import Results from './components/Results'
import SplitText from './components/SplitText'
import GlassSurface from './components/GlassSurface'

interface SystemHealth {
  status: string;
  uptime: number;
  connected_clients: number;
  last_analysis: string | null;
}

const App: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [activeTab, setActiveTab] = useState<'logs' | 'chat'>('logs')
  const [logEntries, setLogEntries] = useState<string[]>([])
  const [analysisResults, setAnalysisResults] = useState<string>('Results will appear here...')

  const checkHealth = async () => {
    try {
      const response = await fetch('/health')
      const data = await response.json()
      setSystemHealth(data)
    } catch (error) {
      console.error('Health check failed:', error)
      setSystemHealth({
        status: 'error',
        uptime: 0,
        connected_clients: 0,
        last_analysis: null
      })
    }
  }

  const pollAnalysisResults = async () => {
    // This function is no longer needed as we handle polling in the QuickActions component
    // The original HTML version doesn't continuously poll /analyze endpoint
    return
  }

  useEffect(() => {
    checkHealth()
    const healthInterval = setInterval(checkHealth, 5000)
    
    return () => {
      clearInterval(healthInterval)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-100 via-dark-200 to-dark-300 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-gradient-radial from-primary-900/10 via-transparent to-transparent" />
      <div className="absolute top-20 left-20 w-72 h-72 bg-primary-500/5 rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute bottom-20 right-20 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl animate-pulse-slow" />
      
      <div className="relative z-10 container mx-auto px-6 py-8 max-w-7xl">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-start justify-between mb-4 gap-8">
            <div className="flex items-center gap-4 flex-1">
              <motion.div 
                className="p-3 bg-primary-500/20 rounded-xl backdrop-blur-sm border border-primary-400/40"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Server className="w-8 h-8 text-primary-400" />
              </motion.div>
              <div>
                <SplitText 
                  text="Windows Log Gathering Agent" 
                  className="text-3xl font-bold text-white"
                  delay={0.05}
                />
                <motion.p 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                  className="text-dark-700 mt-1"
                >
                  Real-time system monitoring and log analysis
                </motion.p>
              </div>
            </div>
            
            <div className="flex-1 max-w-lg">
              <SystemStatus health={systemHealth} />
            </div>
          </div>
        </motion.div>

        {/* Main Content Grid */}
        <div className="space-y-8">
          {/* Quick Actions */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="w-full"
          >
            <GlassSurface className="p-6">
              <QuickActions 
                onLogUpdate={setLogEntries} 
                onResultsUpdate={setAnalysisResults}
              />
            </GlassSurface>
          </motion.div>

          {/* Client Selector */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="w-full"
          >
            <GlassSurface className="p-6">
              <ClientSelector 
                onLogUpdate={setLogEntries} 
                onResultsUpdate={setAnalysisResults}
              />
            </GlassSurface>
          </motion.div>

          {/* Results - Full Width */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="w-full"
          >
            <GlassSurface className="p-6">
              <Results results={analysisResults} />
            </GlassSurface>
          </motion.div>

          {/* Main Display Area */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="w-full"
          >
            {/* Tab Navigation */}
            <div className="flex gap-2 mb-6">
              {[
                { id: 'logs', label: 'Live Logs', icon: Activity },
                { id: 'chat', label: 'Chat Analysis', icon: MessageSquare }
              ].map(({ id, label, icon: Icon }) => (
                <motion.button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                    activeTab === id 
                      ? 'bg-primary-500/20 text-primary-300 border border-primary-400/40' 
                      : 'bg-dark-400/20 text-dark-600 hover:bg-dark-400/30 hover:text-dark-800 border border-dark-400/30'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </motion.button>
              ))}
            </div>

            {/* Tab Content */}
            <GlassSurface className="min-h-[600px]">
              <AnimatePresence mode="wait">
                {activeTab === 'logs' ? (
                  <motion.div
                    key="logs"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <LogViewer entries={logEntries} />
                  </motion.div>
                ) : (
                  <motion.div
                    key="chat"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <ChatInterface />
                  </motion.div>
                )}
              </AnimatePresence>
            </GlassSurface>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

export default App