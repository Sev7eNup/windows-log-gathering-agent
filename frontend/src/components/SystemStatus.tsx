import React from 'react'
import { motion } from 'framer-motion'
import { Activity, Users, Clock, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

interface SystemHealth {
  status: string
  uptime: number
  connected_clients: number
  active_clients?: number
  last_analysis: string | null
  llm_status?: string
  system_metrics?: {
    memory_usage_percent: number
    cpu_usage_percent: number
    active_analyses: number
    cache_size: number
  }
}

interface SystemStatusProps {
  health: SystemHealth | null
}

const SystemStatus: React.FC<SystemStatusProps> = ({ health }) => {
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'ok':
        return 'success'
      case 'warning':
        return 'warning'
      case 'error':
      case 'unhealthy':
        return 'error'
      default:
        return 'warning'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'ok':
        return CheckCircle
      case 'error':
      case 'unhealthy':
        return XCircle
      default:
        return AlertCircle
    }
  }

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m ${Math.floor(seconds % 60)}s`
  }

  if (!health) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-surface p-4"
      >
        <div className="flex items-center gap-3">
          <div className="status-indicator bg-dark-400"></div>
          <span className="text-dark-600 text-sm">Checking status...</span>
        </div>
      </motion.div>
    )
  }

  const statusColor = getStatusColor(health.status)
  const StatusIcon = getStatusIcon(health.status)

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-surface p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <StatusIcon className={`w-5 h-5 ${
            statusColor === 'success' ? 'text-success-400' :
            statusColor === 'warning' ? 'text-warning-400' :
            'text-error-400'
          }`} />
          <span className="font-medium text-white">System Status</span>
        </div>
        <div className={`status-indicator ${
          statusColor === 'success' ? 'bg-success-500' :
          statusColor === 'warning' ? 'bg-warning-500' :
          'bg-error-500'
        }`}></div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary-400" />
          <div>
            <p className="text-dark-600">Status</p>
            <p className={`font-medium capitalize ${
              statusColor === 'success' ? 'text-success-400' :
              statusColor === 'warning' ? 'text-warning-400' :
              'text-error-400'
            }`}>
              {health.status}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-primary-400" />
          <div>
            <p className="text-dark-600">Clients</p>
            <p className="font-medium text-white">
              {health.active_clients ?? 0}/{health.connected_clients}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary-400" />
          <div>
            <p className="text-dark-600">Uptime</p>
            <p className="font-medium text-white">{formatUptime(health.uptime)}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className={`w-4 h-4 rounded-full ${
            health.llm_status === 'connected' ? 'bg-success-400' :
            health.llm_status === 'offline' ? 'bg-error-400' :
            'bg-warning-400'
          }`} />
          <div>
            <p className="text-dark-600">LLM</p>
            <p className={`font-medium text-xs capitalize ${
              health.llm_status === 'connected' ? 'text-success-400' :
              health.llm_status === 'offline' ? 'text-error-400' :
              'text-warning-400'
            }`}>
              {health.llm_status || 'unknown'}
            </p>
          </div>
        </div>
      </div>

      {health.system_metrics && (
        <div className="mt-4 pt-4 border-t border-dark-400/50">
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-dark-600">Memory Usage</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-dark-400/30 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-500 ${
                      health.system_metrics.memory_usage_percent > 80 ? 'bg-error-400' :
                      health.system_metrics.memory_usage_percent > 60 ? 'bg-warning-400' :
                      'bg-success-400'
                    }`}
                    style={{ width: `${Math.min(health.system_metrics.memory_usage_percent, 100)}%` }}
                  />
                </div>
                <span className="text-white font-medium">
                  {health.system_metrics.memory_usage_percent.toFixed(1)}%
                </span>
              </div>
            </div>
            <div>
              <p className="text-dark-600">CPU Usage</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-dark-400/30 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-500 ${
                      health.system_metrics.cpu_usage_percent > 80 ? 'bg-error-400' :
                      health.system_metrics.cpu_usage_percent > 60 ? 'bg-warning-400' :
                      'bg-success-400'
                    }`}
                    style={{ width: `${Math.min(health.system_metrics.cpu_usage_percent, 100)}%` }}
                  />
                </div>
                <span className="text-white font-medium">
                  {health.system_metrics.cpu_usage_percent.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

    </motion.div>
  )
}

export default SystemStatus