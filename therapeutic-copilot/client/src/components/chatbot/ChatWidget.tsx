/**
 * SAATHI AI — Main Chat Widget Component
 * Used in the clinician dashboard for session monitoring and in the embeddable widget.
 *
 * Features:
 * - WebSocket token streaming into live assistant message bubble
 * - Animated typing indicator while waiting for first token
 * - Blinking cursor during active streaming
 * - Crisis banner (red overlay) with Indian helpline numbers
 * - Session end button + summary modal
 * - Auto-scroll on every message / streaming update
 */
import React, { useState, useRef, useEffect } from 'react'
import { useChat, SessionSummary } from '@/hooks/useChat'
import { ChatMessage } from '@/types'

// Indian mental health helplines shown when no backend resources provided
const DEFAULT_HELPLINES = [
  'iCALL: 9152987821',
  'Vandrevala Foundation: 1860-2662-345 (24/7)',
  'AASRA: 9820466627',
]

interface ChatWidgetProps {
  sessionId: string
  patientName?: string
  stage?: 1 | 2 | 3
  onCrisisDetected?: (severity: number) => void
}

export function ChatWidget({
  sessionId,
  patientName = 'Patient',
  stage = 1,
  onCrisisDetected,
}: ChatWidgetProps) {
  const [input, setInput] = useState('')
  const [showSummary, setShowSummary] = useState(false)
  const [summary, setSummary] = useState<SessionSummary | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    isStreaming,
    isConnected,
    crisisDetected,
    crisisResources,
    sendMessage,
    endSession,
    dismissCrisis,
  } = useChat({ sessionId, onCrisisDetected })

  // Auto-scroll on every new message or streaming update
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleEndSession = async () => {
    setSummaryLoading(true)
    setSummaryError(null)
    setSummary(null)
    setShowSummary(true)
    try {
      const result = await endSession()
      setSummary(result)
    } catch {
      setSummaryError('Could not load session summary. Please try again.')
    } finally {
      setSummaryLoading(false)
    }
  }

  const helplines = crisisResources.length > 0 ? crisisResources : DEFAULT_HELPLINES

  return (
    <div className="relative flex flex-col h-full bg-white rounded-xl shadow-lg overflow-hidden">
      {/* ── Crisis Banner ─────────────────────────────────────────────── */}
      {crisisDetected && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-red-50 p-6">
          <div className="bg-white border-2 border-red-500 rounded-xl p-6 max-w-sm w-full shadow-xl">
            <div className="flex items-center mb-3">
              <span className="text-2xl mr-2" aria-hidden>&#128682;</span>
              <h2 className="text-lg font-bold text-red-600">We're here for you</h2>
            </div>
            <p className="text-sm text-gray-700 mb-4">
              It sounds like you may be going through a very difficult time. You are not alone
              — please reach out for immediate support.
            </p>
            <ul className="space-y-1 mb-4">
              {helplines.map((line, i) => (
                <li key={i} className="text-sm font-semibold text-red-700">
                  {line}
                </li>
              ))}
            </ul>
            <button
              onClick={dismissCrisis}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
            >
              I'm safe — continue
            </button>
          </div>
        </div>
      )}

      {/* ── Session Summary Modal ──────────────────────────────────────── */}
      {showSummary && (
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full shadow-xl">
            <h2 className="text-lg font-bold text-gray-900 mb-3">Session Summary</h2>
            {summaryLoading && (
              <div className="flex justify-center py-6">
                <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            {summaryError && (
              <p className="text-sm text-red-600 mb-4">{summaryError}</p>
            )}
            {summary && (
              <>
                <p className="text-sm text-gray-700 mb-3">{summary.summary}</p>
                {summary.keyInsights.length > 0 && (
                  <ul className="text-sm text-gray-600 list-disc list-inside mb-3 space-y-1">
                    {summary.keyInsights.map((insight, i) => (
                      <li key={i}>{insight}</li>
                    ))}
                  </ul>
                )}
                <p className="text-xs text-gray-400">
                  Crisis score: {summary.crisisScore.toFixed(2)}
                </p>
              </>
            )}
            <button
              onClick={() => setShowSummary(false)}
              className="mt-4 w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* ── Header ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between p-4 border-b bg-indigo-600 rounded-t-xl">
        <div>
          <h3 className="font-semibold text-white">Saathi AI</h3>
          <p className="text-xs text-indigo-200">
            Stage {stage} — {patientName}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
          <button
            onClick={handleEndSession}
            className="text-xs text-indigo-200 hover:text-white border border-indigo-400 hover:border-white px-2 py-1 rounded transition-colors"
          >
            End session
          </button>
        </div>
      </div>

      {/* ── Messages ──────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm text-center">
            <p className="font-medium">Hi {patientName}, I'm Saathi.</p>
            <p className="mt-1">How are you feeling today?</p>
          </div>
        )}
        {messages.map((msg, idx) => {
          const isLastAssistant =
            msg.role === 'assistant' && idx === messages.length - 1
          const showCursor = isStreaming && isLastAssistant
          return (
            <MessageBubble key={msg.id} message={msg} showCursor={showCursor} />
          )
        })}
        <div ref={endRef} />
      </div>

      {/* ── Input ─────────────────────────────────────────────────────── */}
      <form onSubmit={handleSubmit} className="p-4 border-t flex space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!isConnected}
          placeholder={isConnected ? 'Type a message...' : 'Connecting...'}
          className="flex-1 px-4 py-2 border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          type="submit"
          disabled={!input.trim() || !isConnected || isStreaming}
          className="px-4 py-2 bg-indigo-600 text-white rounded-full text-sm font-medium disabled:opacity-50 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  )
}

// ── MessageBubble ──────────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: ChatMessage
  showCursor: boolean
}

function MessageBubble({ message, showCursor }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isWaitingForTokens = !isUser && message.content === ''

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-2xl text-sm ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-100 text-gray-800 rounded-bl-sm'
        }`}
      >
        {isWaitingForTokens ? (
          // Animated dots while waiting for the first token
          <span className="flex items-center space-x-1 py-1" aria-label="Thinking">
            <span
              className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: '0ms' }}
            />
            <span
              className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: '150ms' }}
            />
            <span
              className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: '300ms' }}
            />
          </span>
        ) : (
          <>
            {message.content}
            {showCursor && (
              // Blinking cursor appended to the last character while streaming
              <span
                className="inline-block w-0.5 h-3.5 bg-gray-500 ml-0.5 align-middle animate-pulse"
                aria-hidden
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
