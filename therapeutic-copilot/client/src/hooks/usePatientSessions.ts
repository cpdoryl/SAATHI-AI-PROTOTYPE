/**
 * SAATHI AI — usePatientSessions hook
 * Fetches the therapy session list for a given patient.
 */
import { useState, useEffect } from 'react'
import { listPatientSessions } from '@/lib/api'
import { TherapySession } from '@/types'

interface UsePatientSessionsResult {
  sessions: TherapySession[]
  loading: boolean
  error: string | null
  refetch: () => void
}

export function usePatientSessions(patientId: string): UsePatientSessionsResult {
  const [sessions, setSessions] = useState<TherapySession[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!patientId || patientId === 'anonymous') {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    listPatientSessions(patientId)
      .then((res) => {
        const data = res.data
        setSessions(Array.isArray(data) ? data : (data?.sessions ?? []))
      })
      .catch((err: { response?: { data?: { detail?: string } } }) => {
        setError(err.response?.data?.detail ?? 'Failed to load sessions. Please try again.')
      })
      .finally(() => setLoading(false))
  }, [patientId, tick])

  const refetch = () => setTick((t) => t + 1)

  return { sessions, loading, error, refetch }
}
