import React from 'react'
import { motion } from 'framer-motion'
import { FileText, Copy, Download } from 'lucide-react'

interface ResultsProps {
  results: string
  onResultsUpdate?: (results: string) => void
}

const Results: React.FC<ResultsProps> = ({ results }) => {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(results)
  }

  const isJsonResults = results.startsWith('{') || results.startsWith('[')

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-2 h-6 bg-gradient-to-b from-blue-400 to-blue-600 rounded-full"></div>
        <h3 className="text-lg font-semibold text-white">Results</h3>
        
        {results !== 'Results will appear here...' && (
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={copyToClipboard}
              className="p-2 text-primary-400 hover:text-primary-300 transition-colors duration-200 hover:bg-primary-500/20 rounded-lg"
              title="Copy to clipboard"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-[400px] p-6 rounded-xl backdrop-blur-sm bg-dark-200/40 border border-primary-500/20 shadow-xl"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-primary-500/20 rounded-lg">
            <FileText className="w-5 h-5 text-primary-400" />
          </div>
          <span className="text-sm text-primary-300 font-medium">Analysis Output</span>
        </div>
        
        <div className="relative">
          <pre className={`text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isJsonResults 
              ? 'font-mono text-white bg-dark-300/30 p-6 rounded-lg shadow-inner font-medium border border-primary-400/30' 
              : 'text-white bg-dark-300/30 p-6 rounded-lg shadow-inner font-medium border border-primary-400/30'
          }`}>
            {results}
          </pre>
        </div>
      </motion.div>
    </div>
  )
}

export default Results