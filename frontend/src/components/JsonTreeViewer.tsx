import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react'

interface JsonTreeViewerProps {
  data: any
  isOpen: boolean
  onClose: () => void
}

interface JsonNodeProps {
  data: any
  path: string
  level: number
}

const JsonNode: React.FC<JsonNodeProps> = ({ data, path, level }) => {
  const [isExpanded, setIsExpanded] = useState(level < 2) // Auto-expand first 2 levels
  const [copied, setCopied] = useState(false)

  const copyPath = async () => {
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const toggleExpand = () => {
    setIsExpanded(!isExpanded)
  }

  const getValueType = (value: any): string => {
    if (value === null) return 'null'
    if (Array.isArray(value)) return 'array'
    return typeof value
  }

  const getValueDisplay = (value: any): string => {
    const type = getValueType(value)
    switch (type) {
      case 'string':
        return `"${value}"`
      case 'null':
        return 'null'
      case 'array':
        return `[${value.length} items]`
      case 'object':
        return `{${Object.keys(value).length} keys}`
      default:
        return String(value)
    }
  }

  const getTypeColor = (type: string): string => {
    switch (type) {
      case 'string':
        return 'text-green-400'
      case 'number':
        return 'text-blue-400'
      case 'boolean':
        return 'text-purple-400'
      case 'null':
        return 'text-gray-500'
      case 'array':
        return 'text-yellow-400'
      case 'object':
        return 'text-orange-400'
      default:
        return 'text-gray-400'
    }
  }

  const isComplex = (value: any): boolean => {
    return typeof value === 'object' && value !== null
  }

  const type = getValueType(data)
  const isComplexType = isComplex(data)
  const indentation = level * 20

  if (!isComplexType) {
    return (
      <div className="flex items-center gap-2 py-1" style={{ paddingLeft: `${indentation}px` }}>
        <span className="text-primary-300 font-medium">{path}:</span>
        <span className={`${getTypeColor(type)} font-mono text-sm`}>
          {getValueDisplay(data)}
        </span>
        <button
          onClick={copyPath}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-primary-300 transition-all duration-200"
          title="Copy value"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
        </button>
      </div>
    )
  }

  return (
    <div className="group">
      <div 
        className="flex items-center gap-2 py-1 cursor-pointer hover:bg-primary-500/10 rounded px-2 transition-colors duration-200"
        style={{ paddingLeft: `${indentation}px` }}
        onClick={toggleExpand}
      >
        <button className="text-primary-400 hover:text-primary-300">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <span className="text-primary-300 font-medium">{path}:</span>
        <span className={`${getTypeColor(type)} font-mono text-sm`}>
          {getValueDisplay(data)}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            copyPath()
          }}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-primary-300 transition-all duration-200"
          title="Copy object"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
        </button>
      </div>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-l border-primary-500/30 ml-2">
              {Array.isArray(data) ? (
                data.map((item, index) => (
                  <JsonNode
                    key={index}
                    data={item}
                    path={`[${index}]`}
                    level={level + 1}
                  />
                ))
              ) : (
                Object.entries(data).map(([key, value]) => (
                  <JsonNode
                    key={key}
                    data={value}
                    path={key}
                    level={level + 1}
                  />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const JsonTreeViewer: React.FC<JsonTreeViewerProps> = ({ data, isOpen, onClose }) => {
  const [copied, setCopied] = useState(false)

  const copyAll = async () => {
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-start justify-center z-50 p-4 pt-20 overflow-y-auto"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ type: "spring", duration: 0.5 }}
          className="bg-dark-200 rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col border border-primary-500/20"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-primary-500/20">
            <div className="flex items-center gap-3">
              <div className="w-2 h-6 bg-gradient-to-b from-blue-400 to-blue-600 rounded-full"></div>
              <h3 className="text-xl font-semibold text-white">Analysis Details</h3>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={copyAll}
                className="px-4 py-2 bg-primary-500/20 hover:bg-primary-500/30 text-primary-300 rounded-lg transition-colors duration-200 flex items-center gap-2"
                title="Copy all JSON"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span className="text-sm">{copied ? 'Copied!' : 'Copy All'}</span>
              </button>
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-white hover:bg-primary-500/20 rounded-lg transition-colors duration-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-6">
            <div className="bg-dark-300/30 rounded-lg border border-primary-400/30 p-4">
              <JsonNode data={data} path="root" level={0} />
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default JsonTreeViewer