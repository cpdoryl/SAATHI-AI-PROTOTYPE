/**
 * SAATHI AI — useSessionMessages hook
 * Fetches the chat message history for a single therapy session.
 */
import { useState, useEffect } from 'react'
import { getSessionHistory } from '@/lib/api'
import { ChatMessage } from '@/types'

interface UseSessionMessagesResult {
  messages: ChatMessage[]
  loading: boolean
  error: string | null
}

export function useSessionMessages(sessionId: string | null): UseSessionMessagesResult {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) return

    setLoading(true)
    setError(null)

    getSessionHistory(sessionId)
      .then((res) => {
        const data = res.data
        setMessages(Array.isArray(data) ? data : (data?.messages ?? []))
      })
      .catch((err: { response?: { data?: { detail?: string } } }) => {
        setError(err.response?.data?.detail ?? 'Failed to load messages.')
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  return { messages, loading, error }
}
