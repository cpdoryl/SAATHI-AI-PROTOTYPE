/**
 * SAATHI AI — Booking Page
 * Appointment booking flow: select clinician → pick date → pick time slot → confirm.
 * Integrates with POST /api/v1/calendar/events and POST /api/v1/payments/order.
 */
import React, { useState, useEffect } from 'react'
import { createAppointment, listAppointments, cancelAppointment } from '@/lib/api'
import { Appointment } from '@/types'

// ─── Static data (replace with API calls when clinician-list endpoint is ready) ──

const CLINICIANS = [
  { id: 'cli_1', name: 'Dr. Priya Sharma', specialization: 'Anxiety & Depression', available: true },
  { id: 'cli_2', name: 'Dr. Rahul Mehta', specialization: 'Trauma & PTSD', available: true },
  { id: 'cli_3', name: 'Dr. Ananya Nair', specialization: 'Relationships & Family', available: true },
  { id: 'cli_4', name: 'Dr. Vikram Singh', specialization: 'Stress & Burnout', available: true },
]

const TIME_SLOTS = [
  '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
  '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
  '17:00', '17:30', '18:00', '18:30',
]

const SESSION_DURATIONS = [
  { value: 30, label: '30 min  — ₹800' },
  { value: 50, label: '50 min  — ₹1,200' },
  { value: 90, label: '90 min  — ₹1,800' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getNextNDays(n: number): Date[] {
  const days: Date[] = []
  const today = new Date()
  for (let i = 1; i <= n; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() + i)
    if (d.getDay() !== 0) days.push(d)  // skip Sundays
  }
  return days
}

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric' })
}

function formatDateISO(d: Date): string {
  return d.toISOString().split('T')[0]
}

// ─── Step indicator ───────────────────────────────────────────────────────────

const STEPS = ['Clinician', 'Date & Time', 'Confirm']

function StepBar({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {STEPS.map((label, i) => (
        <React.Fragment key={label}>
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold
              ${i < current ? 'bg-indigo-600 text-white'
              : i === current ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
              : 'bg-gray-200 text-gray-500'}`}>
              {i < current ? '✓' : i + 1}
            </div>
            <span className={`mt-1 text-xs ${i === current ? 'text-indigo-700 font-semibold' : 'text-gray-400'}`}>
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`h-0.5 w-16 mx-1 mb-4 ${i < current ? 'bg-indigo-600' : 'bg-gray-200'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  )
}

// ─── Step 1: Clinician selector ───────────────────────────────────────────────

function ClinicianStep({
  selected, onSelect,
}: { selected: string; onSelect: (id: string) => void }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Choose your therapist</h2>
      <div className="grid gap-3">
        {CLINICIANS.map(c => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`w-full text-left px-4 py-4 rounded-xl border-2 transition-all
              ${selected === c.id
                ? 'border-indigo-600 bg-indigo-50 shadow-sm'
                : 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-gray-50'}`}
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-sm">
                {c.name.split(' ').slice(1).map(n => n[0]).join('')}
              </div>
              <div className="flex-1">
                <p className="font-semibold text-gray-800 text-sm">{c.name}</p>
                <p className="text-xs text-gray-500">{c.specialization}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                ${c.available ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'}`}>
                {c.available ? 'Available' : 'Full'}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Step 2: Date & time picker ───────────────────────────────────────────────

function DateTimeStep({
  selectedDate, selectedTime, selectedDuration,
  onDateChange, onTimeChange, onDurationChange,
}: {
  selectedDate: string
  selectedTime: string
  selectedDuration: number
  onDateChange: (d: string) => void
  onTimeChange: (t: string) => void
  onDurationChange: (d: number) => void
}) {
  const days = getNextNDays(14)

  return (
    <div className="space-y-6">
      {/* Date strip */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Select a date</h2>
        <div className="flex gap-2 overflow-x-auto pb-2">
          {days.map(d => {
            const iso = formatDateISO(d)
            return (
              <button
                key={iso}
                onClick={() => onDateChange(iso)}
                className={`flex-shrink-0 flex flex-col items-center px-3 py-2 rounded-xl border-2 text-xs transition-all min-w-[60px]
                  ${selectedDate === iso
                    ? 'border-indigo-600 bg-indigo-600 text-white'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-indigo-300'}`}
              >
                <span className="font-semibold">{d.toLocaleDateString('en-IN', { day: 'numeric' })}</span>
                <span className="opacity-75">{d.toLocaleDateString('en-IN', { month: 'short' })}</span>
                <span className="opacity-75">{d.toLocaleDateString('en-IN', { weekday: 'short' })}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Time grid */}
      {selectedDate && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Select a time slot</h2>
          <div className="grid grid-cols-4 gap-2">
            {TIME_SLOTS.map(slot => (
              <button
                key={slot}
                onClick={() => onTimeChange(slot)}
                className={`px-2 py-2 rounded-lg border-2 text-sm font-medium transition-all
                  ${selectedTime === slot
                    ? 'border-indigo-600 bg-indigo-600 text-white'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-indigo-300'}`}
              >
                {slot}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Duration */}
      {selectedTime && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Session duration</h2>
          <div className="flex gap-3">
            {SESSION_DURATIONS.map(d => (
              <button
                key={d.value}
                onClick={() => onDurationChange(d.value)}
                className={`flex-1 px-3 py-3 rounded-xl border-2 text-sm font-medium transition-all
                  ${selectedDuration === d.value
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-indigo-300'}`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Step 3: Confirm ──────────────────────────────────────────────────────────

function ConfirmStep({
  clinicianId, date, time, duration, onConfirm, loading, error,
}: {
  clinicianId: string
  date: string
  time: string
  duration: number
  onConfirm: () => void
  loading: boolean
  error: string
}) {
  const clinician = CLINICIANS.find(c => c.id === clinicianId)
  const priceMap: Record<number, number> = { 30: 800, 50: 1200, 90: 1800 }
  const price = priceMap[duration] ?? 0

  return (
    <div className="space-y-5">
      <h2 className="text-lg font-semibold text-gray-800">Confirm your appointment</h2>

      <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 space-y-3">
        <Row label="Therapist" value={clinician?.name ?? '—'} />
        <Row label="Specialization" value={clinician?.specialization ?? '—'} />
        <Row label="Date" value={new Date(date).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} />
        <Row label="Time" value={`${time} IST`} />
        <Row label="Duration" value={`${duration} minutes`} />
        <div className="border-t border-indigo-200 pt-3">
          <Row label="Total" value={`₹${price.toLocaleString('en-IN')}`} bold />
        </div>
      </div>

      <p className="text-xs text-gray-500">
        By confirming you agree to the 24-hour cancellation policy.
        A Google Meet link will be emailed to you after payment.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <button
        onClick={onConfirm}
        disabled={loading}
        className="w-full py-3 rounded-xl bg-indigo-600 text-white font-semibold text-sm
          hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Booking…' : `Confirm & Pay ₹${price.toLocaleString('en-IN')}`}
      </button>
    </div>
  )
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={bold ? 'font-bold text-indigo-700 text-base' : 'text-gray-800 font-medium'}>{value}</span>
    </div>
  )
}

// ─── Success screen ───────────────────────────────────────────────────────────

function SuccessScreen({ appointment, onDone }: { appointment: Appointment | null; onDone: () => void }) {
  return (
    <div className="text-center space-y-4 py-6">
      <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto text-3xl">
        ✓
      </div>
      <h2 className="text-xl font-bold text-gray-800">Appointment confirmed!</h2>
      <p className="text-gray-500 text-sm max-w-xs mx-auto">
        A confirmation and Google Meet link will be sent to your registered email address.
      </p>
      {appointment && (
        <p className="text-xs text-gray-400">Booking ID: {appointment.id}</p>
      )}
      <button
        onClick={onDone}
        className="mt-4 px-6 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors"
      >
        Back to Portal
      </button>
    </div>
  )
}

// ─── Upcoming appointments panel ─────────────────────────────────────────────

function UpcomingPanel({
  appointments, onCancel,
}: { appointments: Appointment[]; onCancel: (id: string) => void }) {
  if (appointments.length === 0) return null

  return (
    <div className="mt-8">
      <h3 className="text-base font-semibold text-gray-700 mb-3">Your upcoming appointments</h3>
      <div className="space-y-2">
        {appointments.filter(a => a.status === 'scheduled' || a.status === 'confirmed').map(apt => (
          <div key={apt.id} className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-4 py-3">
            <div>
              <p className="text-sm font-medium text-gray-800">
                {new Date(apt.scheduledAt).toLocaleDateString('en-IN', {
                  weekday: 'short', day: 'numeric', month: 'short',
                })} &nbsp;·&nbsp;
                {new Date(apt.scheduledAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
              </p>
              <p className="text-xs text-gray-500">{apt.durationMinutes} min session</p>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                ${apt.status === 'confirmed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                {apt.status}
              </span>
              <button
                onClick={() => onCancel(apt.id)}
                className="text-xs text-red-500 hover:text-red-700 font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Main BookingPage ─────────────────────────────────────────────────────────

const BookingPage: React.FC = () => {
  const [step, setStep] = useState(0)
  const [clinicianId, setClinicianId] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [duration, setDuration] = useState(50)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [bookedAppointment, setBookedAppointment] = useState<Appointment | null>(null)
  const [appointments, setAppointments] = useState<Appointment[]>([])

  useEffect(() => {
    listAppointments()
      .then((res: any) => setAppointments(res.data?.appointments ?? []))
      .catch(() => {})
  }, [done])

  const canAdvance = [
    clinicianId !== '',
    date !== '' && time !== '',
    true,
  ][step]

  const handleNext = () => {
    if (step < STEPS.length - 1) setStep(s => s + 1)
  }

  const handleBack = () => {
    setError('')
    setStep(s => Math.max(0, s - 1))
  }

  const handleConfirm = async () => {
    setLoading(true)
    setError('')
    try {
      const [hours, minutes] = time.split(':').map(Number)
      const scheduledAt = new Date(`${date}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00+05:30`).toISOString()
      const priceMap: Record<number, number> = { 30: 800, 50: 1200, 90: 1800 }

      const res = await createAppointment({
        clinician_id: clinicianId,
        scheduled_at: scheduledAt,
        duration_minutes: duration,
        amount_inr: priceMap[duration] ?? 1200,
      })

      setBookedAppointment((res as any).data ?? null)
      setDone(true)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Booking failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (id: string) => {
    try {
      await cancelAppointment(id)
      setAppointments(prev => prev.filter(a => a.id !== id))
    } catch {
      // silently ignore
    }
  }

  if (done) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-start justify-center pt-16 px-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 w-full max-w-md p-8">
          <SuccessScreen appointment={bookedAppointment} onDone={() => { setDone(false); setStep(0); setClinicianId(''); setDate(''); setTime(''); setDuration(50) }} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Book a Session</h1>
          <p className="text-sm text-gray-500 mt-1">Choose a therapist and time that works for you</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <StepBar current={step} />

          {step === 0 && (
            <ClinicianStep selected={clinicianId} onSelect={setClinicianId} />
          )}
          {step === 1 && (
            <DateTimeStep
              selectedDate={date}
              selectedTime={time}
              selectedDuration={duration}
              onDateChange={(d) => { setDate(d); setTime('') }}
              onTimeChange={setTime}
              onDurationChange={setDuration}
            />
          )}
          {step === 2 && (
            <ConfirmStep
              clinicianId={clinicianId}
              date={date}
              time={time}
              duration={duration}
              onConfirm={handleConfirm}
              loading={loading}
              error={error}
            />
          )}

          {/* Navigation */}
          <div className="flex justify-between mt-8">
            <button
              onClick={handleBack}
              disabled={step === 0}
              className="px-5 py-2 rounded-xl border border-gray-200 text-sm font-medium text-gray-600
                hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Back
            </button>
            {step < STEPS.length - 1 && (
              <button
                onClick={handleNext}
                disabled={!canAdvance}
                className="px-6 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold
                  hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            )}
          </div>
        </div>

        {/* Upcoming appointments */}
        <UpcomingPanel appointments={appointments} onCancel={handleCancel} />
      </div>
    </div>
  )
}

export default BookingPage
