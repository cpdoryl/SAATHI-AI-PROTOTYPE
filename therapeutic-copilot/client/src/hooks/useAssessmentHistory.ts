/**
 * SAATHI AI — useAssessmentHistory hook
 * Fetches the assessment history for a given patient.
 */
import { useState, useEffect } from 'react'
import { getAssessmentHistory } from '@/lib/api'
import { AssessmentResult } from '@/types'

interface UseAssessmentHistoryResult {
  history: AssessmentResult[]
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAssessmentHistory(patientId: string): UseAssessmentHistoryResult {
  const [history, setHistory] = useState<AssessmentResult[]>([])
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

    getAssessmentHistory(patientId)
      .then((res) => {
        const data = res.data
        setHistory(Array.isArray(data) ? data : (data?.history ?? []))
      })
      .catch((err: { response?: { data?: { detail?: string } } }) => {
        setError(err.response?.data?.detail ?? 'Failed to load assessment history. Please try again.')
      })
      .finally(() => setLoading(false))
  }, [patientId, tick])

  const refetch = () => setTick((t) => t + 1)

  return { history, loading, error, refetch }
}
