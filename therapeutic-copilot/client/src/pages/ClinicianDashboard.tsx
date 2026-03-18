/**
 * SAATHI AI — Clinician Dashboard
 * Main hub for: patient overview, crisis alerts, session monitoring, analytics, appointments.
 */
import React, { useState, useEffect } from 'react'
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { Patient, CrisisAlert, Appointment, TherapySession, AssessmentResult } from '@/types'
import { listPatients, getAnalyticsSummary, listAppointments, createAppointment, cancelAppointment, listPatientSessions, getAssessmentHistory } from '@/lib/api'

// ─── Analytics data shapes ────────────────────────────────────────────────────

interface WeeklySession { day: string; sessions: number }
interface CrisisRatePoint { week: string; crisisRate: number; total: number; crisisCount: number }
interface PatientStageCount { stage: string; count: number }
interface AssessmentScorePoint { type: string; avgScore: number; count: number }

interface AnalyticsSummary {
  weekly_sessions: WeeklySession[]
  crisis_rate: CrisisRatePoint[]
  patient_stages: PatientStageCount[]
  assessment_scores: AssessmentScorePoint[]
  total_active_patients: number
  total_sessions_this_week: number
  crisis_alerts_this_week: number
}

// ─── Stage pie chart colors ───────────────────────────────────────────────────

const STAGE_COLORS: Record<string, string> = {
  LEAD: '#f59e0b',
  ACTIVE: '#22c55e',
  DROPOUT: '#ef4444',
}

// ─── Main dashboard ───────────────────────────────────────────────────────────

export default function ClinicianDashboard() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [crisisAlerts, setCrisisAlerts] = useState<CrisisAlert[]>([])
  const [activeTab, setActiveTab] = useState<'patients' | 'alerts' | 'analytics' | 'appointments'>('patients')
  const [loadingPatients, setLoadingPatients] = useState(true)
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)

  // Load patients from API on mount
  useEffect(() => {
    listPatients()
      .then((res) => setPatients(res.data.patients || []))
      .catch((err) => console.error('Failed to load patients:', err))
      .finally(() => setLoadingPatients(false))
  }, [])

  // Connect to clinician WebSocket for real-time crisis alerts
  useEffect(() => {
    const clinicianId = localStorage.getItem('clinician_id') || ''
    const ws = new WebSocket(`ws://localhost:8000/ws/clinician/${clinicianId}`)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'CRISIS_ALERT') {
        setCrisisAlerts((prev) => [data.data, ...prev])
      }
    }
    return () => ws.close()
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Saathi AI — Clinician Dashboard</h1>
        {crisisAlerts.length > 0 && (
          <div className="flex items-center space-x-2 bg-red-50 border border-red-200 rounded-lg px-3 py-1">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <span className="text-red-700 text-sm font-medium">{crisisAlerts.length} Crisis Alert(s)</span>
          </div>
        )}
      </header>

      {/* Tabs */}
      <div className="px-6 py-4 border-b bg-white">
        {(['patients', 'alerts', 'analytics', 'appointments'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`mr-6 pb-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === tab ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
            {tab === 'alerts' && crisisAlerts.length > 0 && (
              <span className="ml-1 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                {crisisAlerts.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Patient detail drawer */}
      {selectedPatient && (
        <PatientDetailDrawer
          patient={selectedPatient}
          onClose={() => setSelectedPatient(null)}
        />
      )}

      {/* Content */}
      <main className="px-6 py-6">
        {activeTab === 'patients' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Patient Overview</h2>
            {loadingPatients ? (
              <p className="text-gray-400 text-sm">Loading patients...</p>
            ) : patients.length === 0 ? (
              <p className="text-gray-400 text-sm">No patients yet. New leads will appear here.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {patients.map((p) => (
                  <PatientCard key={p.id} patient={p} onClick={() => setSelectedPatient(p)} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'alerts' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Crisis Alerts</h2>
            {crisisAlerts.length === 0 ? (
              <p className="text-gray-400 text-sm">No active crisis alerts.</p>
            ) : (
              <div className="space-y-3">
                {crisisAlerts.map((alert, i) => (
                  <CrisisAlertCard key={i} alert={alert} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'analytics' && <AnalyticsTab />}
        {activeTab === 'appointments' && <AppointmentsTab />}
      </main>
    </div>
  )
}

// ─── Analytics Tab ────────────────────────────────────────────────────────────

function AnalyticsTab() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getAnalyticsSummary()
      .then((res) => setSummary(res.data))
      .catch(() => setError('Failed to load analytics. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-700 font-medium">{error}</p>
        <button
          onClick={() => { setError(null); setLoading(true); getAnalyticsSummary().then((r) => setSummary(r.data)).catch(() => setError('Failed to load analytics.')).finally(() => setLoading(false)) }}
          className="mt-3 text-sm text-indigo-600 underline hover:text-indigo-800"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!summary) return null

  return (
    <div className="space-y-8">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Active Patients" value={summary.total_active_patients} color="text-green-600" />
        <KpiCard label="Sessions This Week" value={summary.total_sessions_this_week} color="text-indigo-600" />
        <KpiCard label="Crisis Alerts (7 days)" value={summary.crisis_alerts_this_week} color="text-red-600" />
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1 — Weekly Sessions BarChart */}
        <ChartCard title="Sessions — Last 7 Days">
          {summary.weekly_sessions.length === 0 ? (
            <EmptyState message="No sessions in the past 7 days." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={summary.weekly_sessions} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#6b7280' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                  formatter={(v: number) => [v, 'Sessions']}
                />
                <Bar dataKey="sessions" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 2 — Crisis Rate AreaChart */}
        <ChartCard title="Crisis Detection Rate — Last 4 Weeks">
          {summary.crisis_rate.every((d) => d.total === 0) ? (
            <EmptyState message="No session data for crisis rate." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={summary.crisis_rate} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                <defs>
                  <linearGradient id="crisisGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="week" tick={{ fontSize: 12, fill: '#6b7280' }} />
                <YAxis
                  tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  domain={[0, 1]}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                  formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'Crisis Rate']}
                />
                <Area
                  type="monotone"
                  dataKey="crisisRate"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fill="url(#crisisGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 3 — Patient Stage PieChart */}
        <ChartCard title="Patient Stage Distribution">
          {summary.patient_stages.every((d) => d.count === 0) ? (
            <EmptyState message="No patient data available." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={summary.patient_stages}
                  dataKey="count"
                  nameKey="stage"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ stage, percent }) =>
                    `${stage} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {summary.patient_stages.map((entry) => (
                    <Cell
                      key={entry.stage}
                      fill={STAGE_COLORS[entry.stage] ?? '#94a3b8'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                  formatter={(v: number, name: string) => [v, name]}
                />
                <Legend
                  iconType="circle"
                  formatter={(value) => (
                    <span style={{ color: '#374151', fontSize: 12 }}>{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* 4 — Assessment Score Distribution BarChart */}
        <ChartCard title="Avg Assessment Score by Type">
          {summary.assessment_scores.length === 0 ? (
            <EmptyState message="No assessment data yet." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart
                data={summary.assessment_scores}
                margin={{ top: 8, right: 16, left: 0, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="type" tick={{ fontSize: 11, fill: '#6b7280' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#6b7280' }} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                  formatter={(v: number, name: string) => [
                    name === 'avgScore' ? v.toFixed(1) : v,
                    name === 'avgScore' ? 'Avg Score' : 'Count',
                  ]}
                />
                <Legend
                  formatter={(value) => (
                    <span style={{ color: '#374151', fontSize: 12 }}>
                      {value === 'avgScore' ? 'Avg Score' : 'Submissions'}
                    </span>
                  )}
                />
                <Bar dataKey="avgScore" fill="#6366f1" radius={[4, 4, 0, 0]} name="avgScore" />
                <Bar dataKey="count" fill="#a5b4fc" radius={[4, 4, 0, 0]} name="count" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>
    </div>
  )
}

// ─── Appointments Tab ─────────────────────────────────────────────────────────

interface AppointmentFormData {
  patientId: string
  scheduledAt: string
  durationMinutes: number
  amountInr: number
}

/** Returns start-of-week (Monday) for the week containing `date`. */
function getWeekStart(date: Date): Date {
  const d = new Date(date)
  const day = d.getDay() // 0=Sun
  const diff = day === 0 ? -6 : 1 - day // shift to Monday
  d.setDate(d.getDate() + diff)
  d.setHours(0, 0, 0, 0)
  return d
}

/** Returns array of 7 Date objects starting from Monday of `weekStart`. */
function getWeekDays(weekStart: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + i)
    return d
  })
}

function AppointmentsTab() {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [weekStart, setWeekStart] = useState<Date>(() => getWeekStart(new Date()))
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<AppointmentFormData>({
    patientId: '',
    scheduledAt: '',
    durationMinutes: 60,
    amountInr: 1500,
  })
  const [formError, setFormError] = useState<string | null>(null)
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const weekDays = getWeekDays(weekStart)

  const fetchAppointments = () => {
    setLoading(true)
    setError(null)
    listAppointments()
      .then((res) => setAppointments(res.data.appointments ?? res.data ?? []))
      .catch(() => setError('Failed to load appointments. Please try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchAppointments()
  }, [])

  // Auto-dismiss toast after 4 s
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(t)
  }, [toast])

  // ── Calendar helpers ────────────────────────────────────────────────────────

  const appointmentsOnDay = (day: Date): Appointment[] =>
    appointments.filter((a) => {
      const d = new Date(a.scheduledAt)
      return (
        d.getFullYear() === day.getFullYear() &&
        d.getMonth() === day.getMonth() &&
        d.getDate() === day.getDate()
      )
    })

  const prevWeek = () =>
    setWeekStart((ws) => { const d = new Date(ws); d.setDate(d.getDate() - 7); return d })

  const nextWeek = () =>
    setWeekStart((ws) => { const d = new Date(ws); d.setDate(d.getDate() + 7); return d })

  const goToday = () => setWeekStart(getWeekStart(new Date()))

  // ── Form handlers ───────────────────────────────────────────────────────────

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'durationMinutes' || name === 'amountInr' ? Number(value) : value,
    }))
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!formData.patientId.trim()) { setFormError('Patient ID is required.'); return }
    if (!formData.scheduledAt) { setFormError('Scheduled date/time is required.'); return }
    if (formData.durationMinutes < 15) { setFormError('Minimum duration is 15 minutes.'); return }
    if (formData.amountInr < 0) { setFormError('Amount cannot be negative.'); return }

    const clinicianId = localStorage.getItem('clinician_id') ?? ''
    setFormSubmitting(true)
    try {
      await createAppointment({
        patient_id: formData.patientId.trim(),
        clinician_id: clinicianId,
        scheduled_at: formData.scheduledAt,
        duration_minutes: formData.durationMinutes,
        amount_inr: formData.amountInr,
      })
      setToast({ message: 'Appointment created successfully.', type: 'success' })
      setShowForm(false)
      setFormData({ patientId: '', scheduledAt: '', durationMinutes: 60, amountInr: 1500 })
      fetchAppointments()
    } catch {
      setFormError('Failed to create appointment. Please try again.')
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleCancel = async (id: string) => {
    if (!window.confirm('Cancel this appointment?')) return
    setCancellingId(id)
    try {
      await cancelAppointment(id)
      setAppointments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'cancelled' } : a))
      )
      setToast({ message: 'Appointment cancelled.', type: 'success' })
    } catch {
      setToast({ message: 'Failed to cancel appointment.', type: 'error' })
    } finally {
      setCancellingId(null)
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  const statusColors: Record<string, string> = {
    scheduled: 'bg-indigo-100 text-indigo-800',
    confirmed: 'bg-green-100 text-green-800',
    completed: 'bg-gray-100 text-gray-600',
    cancelled: 'bg-red-100 text-red-700',
  }

  const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white transition-all ${
            toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-700">Appointments</h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          {showForm ? 'Cancel' : '+ New Appointment'}
        </button>
      </div>

      {/* Create appointment form */}
      {showForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Create Appointment</h3>
          <form onSubmit={handleCreateSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Patient ID</label>
              <input
                name="patientId"
                value={formData.patientId}
                onChange={handleFormChange}
                placeholder="Enter patient UUID"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Date &amp; Time</label>
              <input
                type="datetime-local"
                name="scheduledAt"
                value={formData.scheduledAt}
                onChange={handleFormChange}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Duration (minutes)</label>
              <input
                type="number"
                name="durationMinutes"
                value={formData.durationMinutes}
                onChange={handleFormChange}
                min={15}
                step={15}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Amount (₹)</label>
              <input
                type="number"
                name="amountInr"
                value={formData.amountInr}
                onChange={handleFormChange}
                min={0}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            {formError && (
              <p className="col-span-full text-red-600 text-xs font-medium">{formError}</p>
            )}
            <div className="col-span-full flex justify-end gap-3">
              <button
                type="button"
                onClick={() => { setShowForm(false); setFormError(null) }}
                className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={formSubmitting}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-medium px-5 py-2 rounded-lg flex items-center gap-2 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {formSubmitting && (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {formSubmitting ? 'Creating…' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Weekly calendar */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        {/* Calendar navigation */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
          <button
            onClick={prevWeek}
            className="text-gray-500 hover:text-gray-800 text-sm px-2 py-1 rounded hover:bg-gray-100 focus:outline-none"
            aria-label="Previous week"
          >
            ‹ Prev
          </button>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-gray-700">
              {weekDays[0].toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
              {' – '}
              {weekDays[6].toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
            <button
              onClick={goToday}
              className="text-xs text-indigo-600 hover:text-indigo-800 border border-indigo-200 rounded px-2 py-0.5 hover:bg-indigo-50 focus:outline-none"
            >
              Today
            </button>
          </div>
          <button
            onClick={nextWeek}
            className="text-gray-500 hover:text-gray-800 text-sm px-2 py-1 rounded hover:bg-gray-100 focus:outline-none"
            aria-label="Next week"
          >
            Next ›
          </button>
        </div>

        {/* Calendar grid */}
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="p-6 text-center">
            <p className="text-red-600 text-sm font-medium mb-2">{error}</p>
            <button
              onClick={fetchAppointments}
              className="text-sm text-indigo-600 underline hover:text-indigo-800"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-7 divide-x divide-gray-100">
            {weekDays.map((day, i) => {
              const dayAppts = appointmentsOnDay(day)
              const isToday = day.getTime() === today.getTime()
              return (
                <div key={i} className="min-h-[120px] p-2">
                  <p
                    className={`text-xs font-semibold mb-1 text-center ${
                      isToday ? 'text-indigo-600' : 'text-gray-500'
                    }`}
                  >
                    {DAY_LABELS[i]}
                    <br />
                    <span
                      className={`inline-block w-6 h-6 leading-6 rounded-full text-center ${
                        isToday ? 'bg-indigo-600 text-white' : 'text-gray-700'
                      }`}
                    >
                      {day.getDate()}
                    </span>
                  </p>
                  {dayAppts.length === 0 ? (
                    <p className="text-gray-300 text-xs text-center mt-2">—</p>
                  ) : (
                    <div className="space-y-1">
                      {dayAppts.map((a) => (
                        <div
                          key={a.id}
                          className={`text-xs rounded px-1.5 py-1 leading-tight ${statusColors[a.status] ?? 'bg-gray-100 text-gray-600'}`}
                          title={`${a.status} | ${a.durationMinutes} min | ₹${a.amountInr}`}
                        >
                          {new Date(a.scheduledAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Appointment list */}
      {!loading && !error && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700">All Appointments</h3>
          </div>
          {appointments.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <svg className="w-12 h-12 mb-3 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p className="text-sm">No appointments yet. Create one above.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {appointments.map((a) => (
                <AppointmentRow
                  key={a.id}
                  appointment={a}
                  onCancel={handleCancel}
                  cancellingId={cancellingId}
                  statusColors={statusColors}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function AppointmentRow({
  appointment: a,
  onCancel,
  cancellingId,
  statusColors,
}: {
  appointment: Appointment
  onCancel: (id: string) => void
  cancellingId: string | null
  statusColors: Record<string, string>
}) {
  const canCancel = a.status === 'scheduled' || a.status === 'confirmed'
  return (
    <div className="flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[a.status] ?? 'bg-gray-100 text-gray-600'}`}
          >
            {a.status}
          </span>
          <span className="text-sm font-medium text-gray-800">
            {new Date(a.scheduledAt).toLocaleString('en-IN', {
              day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
            })}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>Patient: <span className="font-mono">{a.patientId}</span></span>
          <span>{a.durationMinutes} min</span>
          <span>₹{a.amountInr.toLocaleString('en-IN')}</span>
          <span className={a.paymentStatus === 'paid' ? 'text-green-600 font-medium' : 'text-yellow-600'}>
            {a.paymentStatus}
          </span>
        </div>
      </div>
      {canCancel && (
        <button
          onClick={() => onCancel(a.id)}
          disabled={cancellingId === a.id}
          className="ml-4 text-xs text-red-600 hover:text-red-800 border border-red-200 hover:border-red-400 rounded px-3 py-1 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400"
        >
          {cancellingId === a.id ? (
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
              Cancelling…
            </span>
          ) : 'Cancel'}
        </button>
      )}
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function KpiCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-5">
      <h3 className="text-sm font-semibold text-gray-600 mb-4">{title}</h3>
      {children}
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-40 text-gray-400 text-sm">{message}</div>
  )
}

function RiskBadge({ score }: { score: number }) {
  const pct = (score * 100).toFixed(0)
  if (score > 0.7) {
    return (
      <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-red-100 text-red-700" title={`Dropout risk: ${pct}%`}>
        {pct}% risk
      </span>
    )
  }
  if (score >= 0.3) {
    return (
      <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-yellow-100 text-yellow-700" title={`Dropout risk: ${pct}%`}>
        {pct}% risk
      </span>
    )
  }
  return (
    <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-green-100 text-green-700" title={`Dropout risk: ${pct}%`}>
      {pct}% risk
    </span>
  )
}

function PatientCard({ patient, onClick }: { patient: Patient; onClick: () => void }) {
  const stageColors = { lead: 'bg-yellow-100 text-yellow-800', active: 'bg-green-100 text-green-800', dropout: 'bg-red-100 text-red-800', archived: 'bg-gray-100 text-gray-600' }
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-white rounded-lg shadow-sm p-4 border border-gray-100 hover:border-indigo-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all cursor-pointer"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="font-medium text-gray-900 truncate">{patient.fullName || 'Anonymous'}</h3>
          <RiskBadge score={patient.dropoutRiskScore} />
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${stageColors[patient.stage]}`}>
          {patient.stage}
        </span>
      </div>
      <p className="text-xs text-gray-500">Last Active: {new Date(patient.lastActive).toLocaleDateString()}</p>
    </button>
  )
}

function CrisisAlertCard({ alert }: { alert: CrisisAlert }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-1">
        <span className="font-medium text-red-800 text-sm">Crisis Detected — Severity {alert.severity}/10</span>
        <span className="text-xs text-red-500">{new Date(alert.timestamp).toLocaleTimeString()}</span>
      </div>
      <p className="text-xs text-red-700">Keywords: {alert.detectedKeywords?.join(', ')}</p>
      <p className="text-xs text-red-600 mt-1">Session: {alert.sessionId}</p>
    </div>
  )
}

// ─── Patient Detail Drawer ─────────────────────────────────────────────────────

const SESSION_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  crisis_escalated: 'bg-red-100 text-red-700',
}

function PatientDetailDrawer({
  patient,
  onClose,
}: {
  patient: Patient
  onClose: () => void
}) {
  const [sessions, setSessions] = useState<TherapySession[]>([])
  const [lastPhq9, setLastPhq9] = useState<AssessmentResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      listPatientSessions(patient.id),
      getAssessmentHistory(patient.id),
    ])
      .then(([sessionsRes, assessmentsRes]) => {
        const sessionList: TherapySession[] = sessionsRes.data.sessions ?? sessionsRes.data ?? []
        setSessions(sessionList)

        const assessments: AssessmentResult[] = assessmentsRes.data.assessments ?? assessmentsRes.data ?? []
        const phq9List = assessments
          .filter((a) => a.assessmentType?.toLowerCase().includes('phq'))
          .sort((a, b) => new Date(b.administeredAt).getTime() - new Date(a.administeredAt).getTime())
        setLastPhq9(phq9List[0] ?? null)
      })
      .catch(() => setError('Failed to load patient details.'))
      .finally(() => setLoading(false))
  }, [patient.id])

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const stageColors = {
    lead: 'bg-yellow-100 text-yellow-800',
    active: 'bg-green-100 text-green-800',
    dropout: 'bg-red-100 text-red-800',
    archived: 'bg-gray-100 text-gray-600',
  }

  const recentSessions = sessions.slice(0, 5)

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Patient details for ${patient.fullName}`}
        className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-xl flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Patient Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded p-1 transition-colors"
            aria-label="Close drawer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Patient info */}
          <section>
            <div className="flex items-center gap-3 mb-3">
              {/* Avatar placeholder */}
              <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                <span className="text-indigo-600 font-bold text-lg">
                  {(patient.fullName || 'A').charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-gray-900 truncate">{patient.fullName || 'Anonymous'}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${stageColors[patient.stage]}`}>
                    {patient.stage}
                  </span>
                  <RiskBadge score={patient.dropoutRiskScore} />
                </div>
              </div>
            </div>

            <dl className="space-y-2 text-sm">
              {patient.email && (
                <div className="flex items-center gap-2">
                  <dt className="text-gray-500 w-20 flex-shrink-0">Email</dt>
                  <dd className="text-gray-800 truncate">{patient.email}</dd>
                </div>
              )}
              {patient.phone && (
                <div className="flex items-center gap-2">
                  <dt className="text-gray-500 w-20 flex-shrink-0">Phone</dt>
                  <dd className="text-gray-800">{patient.phone}</dd>
                </div>
              )}
              <div className="flex items-center gap-2">
                <dt className="text-gray-500 w-20 flex-shrink-0">Language</dt>
                <dd className="text-gray-800 uppercase">{patient.language}</dd>
              </div>
              <div className="flex items-center gap-2">
                <dt className="text-gray-500 w-20 flex-shrink-0">Last Active</dt>
                <dd className="text-gray-800">
                  {new Date(patient.lastActive).toLocaleDateString('en-IN', {
                    day: 'numeric', month: 'short', year: 'numeric',
                  })}
                </dd>
              </div>
            </dl>
          </section>

          {/* Stats row */}
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <div className="w-7 h-7 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
              {error}
            </div>
          ) : (
            <>
              {/* KPI strip */}
              <section className="grid grid-cols-3 gap-3">
                <div className="bg-indigo-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-indigo-600">{sessions.length}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Sessions</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-purple-600">
                    {lastPhq9 ? lastPhq9.score : '—'}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Last PHQ-9</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-700">
                    {(patient.dropoutRiskScore * 100).toFixed(0)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">Risk Score</p>
                </div>
              </section>

              {/* PHQ-9 severity */}
              {lastPhq9 && (
                <section>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                    PHQ-9 Assessment
                  </h3>
                  <div className="bg-white border border-gray-100 rounded-lg px-4 py-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        Score: <span className="text-indigo-600">{lastPhq9.score}</span>
                        <span className="ml-2 text-xs text-gray-500 font-normal capitalize">
                          ({lastPhq9.severity})
                        </span>
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {new Date(lastPhq9.administeredAt).toLocaleDateString('en-IN', {
                          day: 'numeric', month: 'short', year: 'numeric',
                        })}
                      </p>
                    </div>
                  </div>
                </section>
              )}

              {/* Recent sessions */}
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Recent Sessions {sessions.length > 5 && `(showing 5 of ${sessions.length})`}
                </h3>
                {recentSessions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                    <svg className="w-10 h-10 mb-2 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <p className="text-sm">No sessions yet.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {recentSessions.map((s) => (
                      <div
                        key={s.id}
                        className="bg-white border border-gray-100 rounded-lg px-4 py-3"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SESSION_STATUS_COLORS[s.status] ?? 'bg-gray-100 text-gray-600'}`}>
                            {s.status.replace('_', ' ')}
                          </span>
                          <span className="text-xs text-gray-400">
                            Stage {s.stage}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>
                            {new Date(s.startedAt).toLocaleDateString('en-IN', {
                              day: 'numeric', month: 'short', year: 'numeric',
                            })}
                          </span>
                          {s.crisisScore > 0 && (
                            <span className={`font-medium ${s.crisisScore > 0.7 ? 'text-red-600' : s.crisisScore >= 0.3 ? 'text-yellow-600' : 'text-gray-500'}`}>
                              Crisis: {(s.crisisScore * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </>
  )
}
