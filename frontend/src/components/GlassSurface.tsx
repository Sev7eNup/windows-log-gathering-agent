import React from 'react'
import { motion } from 'framer-motion'

interface GlassSurfaceProps {
  children: React.ReactNode
  className?: string
}

const GlassSurface: React.FC<GlassSurfaceProps> = ({ children, className = '' }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={`glass-surface ${className}`}
    >
      {children}
    </motion.div>
  )
}

export default GlassSurface