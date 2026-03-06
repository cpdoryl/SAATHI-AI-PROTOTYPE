/**
 * SAATHI AI — Main Chat Widget Component
 * Used in the clinician dashboard for session monitoring and in the embeddable widget.
 */
import React, { useState, useRef, useEffect } from 'react'
import { useChat } from '@/hooks/useChat'
import { ChatMessage } from '@/types'

interface ChatWidgetProps {
  sessionId: string
  patientName?: string
  stage?: 1 | 2 | 3
  onCrisisDetected?: (severity: number) => void
}

export function ChatWidget({ sessionId, patientName = 'Patient', stage = 1, onCrisisDetected }: ChatWidgetProps) {
  const [input, setInput] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const { messages, isTyping, isConnected, sendMessage } = useChat({ sessionId, onCrisisDetected })

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMessage(input.trim())
    setInput('')
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-indigo-600 rounded-t-xl">
        <div>
          <h3 className="font-semibold text-white">Saathi AI</h3>
          <p className="text-xs text-indigo-200">Stage {stage} — {patientName}</p>
        </div>
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isTyping && (
          <div className="flex items-center space-x-1 text-gray-400 text-sm">
            <span className="animate-bounce">●</span>
            <span className="animate-bounce delay-75">●</span>
            <span className="animate-bounce delay-150">●</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t flex space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          className="flex-1 px-4 py-2 border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={!input.trim() || !isConnected}
          className="px-4 py-2 bg-indigo-600 text-white rounded-full text-sm font-medium disabled:opacity-50 hover:bg-indigo-700"
        >
          Send
        </button>
      </form>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-2xl text-sm ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
        }`}
      >
        {message.content}
      </div>
    </div>
  )
}
