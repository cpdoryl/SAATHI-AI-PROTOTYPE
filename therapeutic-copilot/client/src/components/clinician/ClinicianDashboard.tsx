/**
 * SAATHI AI — Clinician Dashboard
 * Main hub for: patient overview, crisis alerts, session monitoring, analytics.
 */
import React, { useState, useEffect } from 'react'
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { Patient, CrisisAlert } from '@/types'
import { listPatients, getAnalyticsSummary } from '@/lib/api'

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

export function ClinicianDashboard() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [crisisAlerts, setCrisisAlerts] = useState<CrisisAlert[]>([])
  const [activeTab, setActiveTab] = useState<'patients' | 'alerts' | 'analytics'>('patients')
  const [loadingPatients, setLoadingPatients] = useState(true)

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
        {(['patients', 'alerts', 'analytics'] as const).map((tab) => (
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
                  <PatientCard key={p.id} patient={p} />
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

function PatientCard({ patient }: { patient: Patient }) {
  const stageColors = { lead: 'bg-yellow-100 text-yellow-800', active: 'bg-green-100 text-green-800', dropout: 'bg-red-100 text-red-800', archived: 'bg-gray-100 text-gray-600' }
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 border border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium text-gray-900">{patient.fullName || 'Anonymous'}</h3>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${stageColors[patient.stage]}`}>
          {patient.stage}
        </span>
      </div>
      <p className="text-xs text-gray-500">Risk Score: {(patient.dropoutRiskScore * 100).toFixed(0)}%</p>
      <p className="text-xs text-gray-500">Last Active: {new Date(patient.lastActive).toLocaleDateString()}</p>
    </div>
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
