import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal, Clock, AlertTriangle, Info, CheckCircle, XCircle, ScrollText } from 'lucide-react'

interface LogEntry {
  message: string
  timestamp: string
  type: 'info' | 'warning' | 'error' | 'success' | 'debug'
  id: string
}

interface LogViewerProps {
  entries: string[]
}

const LogViewer: React.FC<LogViewerProps> = ({ entries }) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [logEntries, setLogEntries] = useState<LogEntry[]>([])

  // Convert string entries to LogEntry objects with real-time timestamps
  useEffect(() => {
    if (entries.length === 0) {
      setLogEntries([])
      return
    }

    // Only process new entries that aren't already in our state
    const existingIds = new Set(logEntries.map(entry => entry.id))
    const newEntries: LogEntry[] = []
    
    entries.forEach((entry, index) => {
      const id = `entry-${entries.length}-${index}`
      if (!existingIds.has(id)) {
        newEntries.push({
          message: entry,
          timestamp: new Date().toLocaleTimeString('en-US', { 
            hour12: true, 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          }),
          type: getLogType(entry),
          id
        })
      }
    })

    if (newEntries.length > 0) {
      setLogEntries(prevEntries => [...newEntries, ...prevEntries].slice(0, 100)) // Keep latest 100 entries
    }
  }, [entries])

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      // Use requestAnimationFrame for smoother scrolling
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
      })
    }
  }, [logEntries, autoScroll])

  // Initial scroll to bottom when component mounts
  useEffect(() => {
    if (scrollRef.current && logEntries.length === 0) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [])

  const getLogType = (entry: string): 'info' | 'warning' | 'error' | 'success' | 'debug' => {
    const lowerEntry = entry.toLowerCase()
    if (lowerEntry.includes('❌') || lowerEntry.includes('error') || lowerEntry.includes('failed') || lowerEntry.includes('exception')) {
      return 'error'
    }
    if (lowerEntry.includes('⚠️') || lowerEntry.includes('warning') || lowerEntry.includes('warn')) {
      return 'warning'
    }
    if (lowerEntry.includes('✅') || lowerEntry.includes('completed') || lowerEntry.includes('success') || lowerEntry.includes('found')) {
      return 'success'
    }
    if (lowerEntry.includes('📡') || lowerEntry.includes('📥') || lowerEntry.includes('api call') || lowerEntry.includes('response')) {
      return 'debug'
    }
    return 'info'
  }

  const getIcon = (type: string) => {
    switch (type) {
      case 'error': return XCircle
      case 'warning': return AlertTriangle
      case 'success': return CheckCircle
      case 'debug': return ScrollText
      default: return Info
    }
  }

  const toggleAutoScroll = () => {
    setAutoScroll(!autoScroll)
  }

  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10
      
      // If user scrolls up, disable auto-scroll; if they scroll to bottom, enable it
      if (!isAtBottom && autoScroll) {
        setAutoScroll(false)
      } else if (isAtBottom && !autoScroll) {
        setAutoScroll(true)
      }
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-500/20 rounded-lg">
          <Terminal className="w-5 h-5 text-primary-400" />
        </div>
        <h3 className="text-lg font-semibold text-white">Live Process Log</h3>
        
        <div className="ml-auto flex items-center gap-4">
          {entries.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-dark-600">
              <div className="status-indicator bg-success-500"></div>
              <span>{entries.length} entries</span>
            </div>
          )}
          
          <button
            onClick={toggleAutoScroll}
            className={`px-3 py-1 text-xs rounded-lg transition-all duration-200 ${
              autoScroll 
                ? 'bg-success-500/20 text-success-300 border border-success-400/30' 
                : 'bg-dark-400/20 text-dark-600 border border-dark-400/30 hover:bg-dark-400/30'
            }`}
          >
            Auto-scroll: {autoScroll ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-96 overflow-y-auto space-y-2 scrollbar-thin scrollbar-track-dark-300 scrollbar-thumb-primary-500 pr-2"
        style={{ scrollBehavior: autoScroll ? 'smooth' : 'auto' }}
      >
        <AnimatePresence initial={false}>
          {logEntries.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-dark-600"
            >
              <Terminal className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-lg">No activity yet</p>
              <p className="text-sm">Use Quick Actions to start monitoring</p>
            </motion.div>
          ) : (
            // Show entries in chronological order (oldest first, newest at bottom for autoscroll)
            logEntries.slice().reverse().map((entry, index) => {
              const Icon = getIcon(entry.type)
              
              return (
                <motion.div
                  key={`${entry.message}-${logEntries.length - index}`}
                  initial={{ opacity: 0, x: -20, scale: 0.95 }}
                  animate={{ opacity: 1, x: 0, scale: 1 }}
                  transition={{ duration: 0.2 }}
                  className={`log-entry ${entry.type} p-3 rounded-lg border-l-4 transition-all duration-200 hover:shadow-lg hover:translate-x-1 ${
                    entry.type === 'error' ? 'bg-error-500/10 border-error-500 text-dark-800' :
                    entry.type === 'warning' ? 'bg-warning-500/10 border-warning-500 text-dark-800' :
                    entry.type === 'success' ? 'bg-success-500/10 border-success-500 text-dark-800' :
                    entry.type === 'debug' ? 'bg-primary-500/10 border-primary-500 text-dark-800' :
                    'bg-dark-300/20 border-dark-600 text-dark-700'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                      entry.type === 'error' ? 'text-error-500' :
                      entry.type === 'warning' ? 'text-warning-500' :
                      entry.type === 'success' ? 'text-success-500' :
                      entry.type === 'debug' ? 'text-primary-500' :
                      'text-dark-600'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-mono leading-relaxed break-words whitespace-pre-wrap font-medium">{entry.message}</p>
                    </div>
                    <div className="flex items-center gap-1 text-xs opacity-70 flex-shrink-0">
                      <Clock className="w-3 h-3" />
                      <span>{entry.timestamp}</span>
                    </div>
                  </div>
                </motion.div>
              )
            })
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default LogViewer