/**
 * SAATHI AI — useAppointments hook
 * Fetches the appointment list for the authenticated user.
 */
import { useState, useEffect } from 'react'
import { listAppointments, cancelAppointment as cancelAppointmentApi } from '@/lib/api'
import { Appointment } from '@/types'

// The backend returns snake_case keys; map them to the Appointment interface.
function mapAppointment(raw: Record<string, unknown>): Appointment {
  return {
    id: (raw.appointment_id ?? raw.id) as string,
    patientId: raw.patient_id as string,
    clinicianId: (raw.clinician_id ?? '') as string,
    scheduledAt: raw.scheduled_at as string,
    durationMinutes: (raw.duration_minutes ?? 60) as number,
    status: (raw.status ?? 'scheduled') as Appointment['status'],
    amountInr: (raw.amount_inr ?? 0) as number,
    paymentStatus: (raw.payment_status ?? 'pending') as string,
  }
}

interface UseAppointmentsResult {
  appointments: Appointment[]
  loading: boolean
  error: string | null
  refetch: () => void
  cancel: (id: string) => Promise<void>
}

export function useAppointments(): UseAppointmentsResult {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    setLoading(true)
    setError(null)

    listAppointments()
      .then((res) => {
        const data = res.data
        const raw: Record<string, unknown>[] = Array.isArray(data)
          ? data
          : (data?.appointments ?? [])
        setAppointments(raw.map(mapAppointment))
      })
      .catch((err: { response?: { data?: { detail?: string } } }) => {
        setError(err.response?.data?.detail ?? 'Failed to load appointments. Please try again.')
      })
      .finally(() => setLoading(false))
  }, [tick])

  const refetch = () => setTick((t) => t + 1)

  const cancel = async (id: string): Promise<void> => {
    await cancelAppointmentApi(id)
    setAppointments((prev) =>
      prev.map((a) => (a.id === id ? { ...a, status: 'cancelled' } : a))
    )
  }

  return { appointments, loading, error, refetch, cancel }
}
