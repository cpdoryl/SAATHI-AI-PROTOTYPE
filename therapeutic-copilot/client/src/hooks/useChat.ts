/**
 * SAATHI AI — useChat hook
 * Manages WebSocket connection for real-time AI response streaming.
 * Supports both new token streaming protocol and legacy AI_TYPING/AI_RESPONSE protocol.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { ChatMessage } from '@/types'

interface UseChatOptions {
  sessionId: string
  onCrisisDetected?: (severity: number) => void
}

export interface SessionSummary {
  summary: string
  keyInsights: string[]
  crisisScore: number
}

function getWsBase(): string {
  const envUrl = (import.meta as Record<string, unknown> & { env: Record<string, string> }).env.VITE_WS_URL
  if (envUrl) return envUrl
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}`
}

export function useChat({ sessionId, onCrisisDetected }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [crisisDetected, setCrisisDetected] = useState(false)
  const [crisisResources, setCrisisResources] = useState<string[]>([])

  const wsRef = useRef<WebSocket | null>(null)
  const streamingIdRef = useRef<string | null>(null)
  // Stable ref to the callback so we never need to re-open the socket when the prop changes
  const onCrisisRef = useRef(onCrisisDetected)
  onCrisisRef.current = onCrisisDetected

  useEffect(() => {
    const ws = new WebSocket(`${getWsBase()}/ws/chat/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)

    ws.onclose = () => {
      setIsConnected(false)
      setIsStreaming(false)
    }

    ws.onerror = () => {
      setIsConnected(false)
      setIsStreaming(false)
    }

    ws.onmessage = (event: MessageEvent) => {
      let data: Record<string, unknown>
      try {
        data = JSON.parse(event.data as string) as Record<string, unknown>
      } catch {
        return
      }

      // ── New streaming protocol ──────────────────────────────────────────
      if (data.type === 'token') {
        const token = String(data.token ?? '')
        setMessages((prev) =>
          prev.map((m) =>
            m.id === streamingIdRef.current ? { ...m, content: m.content + token } : m,
          ),
        )
        return
      }

      if (data.type === 'done') {
        setIsStreaming(false)
        streamingIdRef.current = null
        return
      }

      if (data.type === 'crisis') {
        setCrisisDetected(true)
        setCrisisResources((data.resources as string[]) ?? [])
        onCrisisRef.current?.((data.severity as number) ?? 1)
        return
      }

      // ── Legacy protocol (backward compat) ──────────────────────────────
      if (data.type === 'AI_TYPING') {
        // Create streaming placeholder only if one doesn't exist yet
        if (!streamingIdRef.current) {
          const id = `stream-${Date.now()}`
          streamingIdRef.current = id
          setMessages((prev) => [
            ...prev,
            {
              id,
              sessionId,
              role: 'assistant',
              content: '',
              createdAt: new Date().toISOString(),
            },
          ])
        }
        setIsStreaming(true)
        return
      }

      if (data.type === 'AI_RESPONSE') {
        const msg = data.message as ChatMessage
        setMessages((prev) => {
          const sid = streamingIdRef.current
          if (sid) return prev.map((m) => (m.id === sid ? msg : m))
          return [...prev, msg]
        })
        setIsStreaming(false)
        streamingIdRef.current = null
        return
      }

      if (data.type === 'CRISIS_ALERT') {
        setCrisisDetected(true)
        setCrisisResources((data.resources as string[]) ?? [])
        onCrisisRef.current?.((data.severity as number) ?? 1)
        return
      }
    }

    return () => ws.close()
  }, [sessionId])

  const sendMessage = useCallback(
    (content: string) => {
      const ws = wsRef.current
      if (!ws || ws.readyState !== WebSocket.OPEN) return

      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        sessionId,
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      }

      // Create streaming placeholder for the assistant reply
      const streamId = `stream-${Date.now() + 1}`
      streamingIdRef.current = streamId
      const placeholder: ChatMessage = {
        id: streamId,
        sessionId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, userMsg, placeholder])
      setIsStreaming(true)

      ws.send(JSON.stringify({ type: 'USER_MESSAGE', content, sessionId }))
    },
    [sessionId],
  )

  const endSession = useCallback(async (): Promise<SessionSummary> => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'END_SESSION', sessionId }))
    }
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/sessions/${sessionId}/summary`, {
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
    if (!res.ok) throw new Error(`Summary fetch failed: ${res.status}`)
    return res.json() as Promise<SessionSummary>
  }, [sessionId])

  const dismissCrisis = useCallback(() => {
    setCrisisDetected(false)
    setCrisisResources([])
  }, [])

  return {
    messages,
    sendMessage,
    endSession,
    dismissCrisis,
    isStreaming,
    isConnected,
    crisisDetected,
    crisisResources,
    // Legacy alias so older call sites don't break
    isTyping: isStreaming,
  }
}
