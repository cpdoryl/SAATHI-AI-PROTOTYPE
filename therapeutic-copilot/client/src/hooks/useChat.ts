/**
 * SAATHI AI — useChat hook
 * Manages WebSocket connection for real-time AI response streaming.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { ChatMessage } from '@/types'

interface UseChatOptions {
  sessionId: string
  onCrisisDetected?: (severity: number) => void
}

export function useChat({ sessionId, onCrisisDetected }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'CRISIS_ALERT' && onCrisisDetected) {
        onCrisisDetected(data.severity)
      } else if (data.type === 'AI_RESPONSE') {
        setIsTyping(false)
        setMessages((prev) => [...prev, data.message])
      } else if (data.type === 'AI_TYPING') {
        setIsTyping(true)
      }
    }

    return () => ws.close()
  }, [sessionId])

  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    const msg = { type: 'USER_MESSAGE', content, sessionId }
    wsRef.current.send(JSON.stringify(msg))
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), sessionId, role: 'user', content, createdAt: new Date().toISOString() },
    ])
    setIsTyping(true)
  }, [sessionId])

  return { messages, isTyping, isConnected, sendMessage }
}
