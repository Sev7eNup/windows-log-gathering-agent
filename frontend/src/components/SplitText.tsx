import React from 'react'
import { motion } from 'framer-motion'

interface SplitTextProps {
  text: string
  className?: string
  delay?: number
}

const SplitText: React.FC<SplitTextProps> = ({ text, className = '', delay = 0.05 }) => {
  const words = text.split(' ')

  return (
    <div className={className}>
      {words.map((word, wordIndex) => (
        <span key={wordIndex} className="inline-block">
          {word.split('').map((char, charIndex) => (
            <motion.span
              key={charIndex}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: (wordIndex * word.length + charIndex) * delay,
                duration: 0.3
              }}
              className="inline-block"
            >
              {char}
            </motion.span>
          ))}
          <span> </span>
        </span>
      ))}
    </div>
  )
}

export default SplitText