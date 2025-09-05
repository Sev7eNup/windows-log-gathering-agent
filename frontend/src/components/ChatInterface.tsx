import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Loader2, MessageSquare } from 'lucide-react'

interface Message {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: inputValue }),
      })

      const data = await response.json()
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response || 'Sorry, I could not process your request.',
        sender: 'bot',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Failed to get response. Please check if the LLM service is running.',
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-600/20 rounded-lg">
          <MessageSquare className="w-5 h-5 text-primary-400" />
        </div>
        <h3 className="text-lg font-semibold text-white">Chat Analysis</h3>
        <div className="ml-auto flex items-center gap-2 text-sm text-gray-400">
          <div className="status-indicator bg-blue-500"></div>
          <span>AI Assistant</span>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 scrollbar-thin scrollbar-track-gray-800 scrollbar-thumb-gray-600">
        {messages.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center h-full text-gray-500"
          >
            <Bot className="w-12 h-12 mb-4 opacity-50" />
            <p className="text-lg">Start a conversation</p>
            <p className="text-sm">Ask about your logs or system status</p>
          </motion.div>
        ) : (
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.3 }}
                className={`flex gap-3 ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.sender === 'bot' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-primary-600/20 rounded-full flex items-center justify-center">
                      <Bot className="w-4 h-4 text-primary-400" />
                    </div>
                  </div>
                )}
                
                <div className={`max-w-[80%] ${message.sender === 'user' ? 'order-last' : ''}`}>
                  <div
                    className={`p-3 rounded-xl ${
                      message.sender === 'user'
                        ? 'bg-primary-600/30 text-white ml-auto'
                        : 'bg-gray-700/50 text-gray-100'
                    }`}
                  >
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 px-1">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>

                {message.sender === 'user' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-gray-600/20 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-gray-400" />
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-3 justify-start"
          >
            <div className="w-8 h-8 bg-primary-600/20 rounded-full flex items-center justify-center">
              <Bot className="w-4 h-4 text-primary-400" />
            </div>
            <div className="bg-gray-700/50 p-3 rounded-xl">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary-400" />
                <span className="text-sm text-gray-300">Thinking...</span>
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-700/50 pt-4">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about logs, system status, or analysis results..."
              disabled={isLoading}
              rows={1}
              className="w-full p-3 pr-12 bg-gray-800/50 border border-gray-700/50 rounded-xl 
                       text-white placeholder-gray-500 resize-none focus:outline-none 
                       focus:border-primary-500/50 focus:bg-gray-800/70 transition-all duration-200
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
          <motion.button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isLoading}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-4 py-3 bg-primary-600/20 hover:bg-primary-600/30 border border-primary-500/30 
                     hover:border-primary-500/50 rounded-xl transition-all duration-200 
                     disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
            ) : (
              <Send className="w-5 h-5 text-primary-400" />
            )}
          </motion.button>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface