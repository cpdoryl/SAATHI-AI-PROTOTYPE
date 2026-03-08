/**
 * SAATHI AI — Patient Portal
 * Patient-facing interface for session history, assessments, and appointments.
 */
import React, { useState } from 'react'
import { format } from 'date-fns'
import { getAssessmentQuestions, submitAssessment } from '@/lib/api'
import { usePatientSessions } from '@/hooks/usePatientSessions'
import { useSessionMessages } from '@/hooks/useSessionMessages'
import { TherapySession, ChatMessage } from '@/types'

// ─── Types ────────────────────────────────────────────────────────────────────

type Question = { id: number; text: string; scale: number[]; labels: string[] }
type AssessmentResult = {
  assessment_type: string
  total_score: number
  severity: string
  max_possible: number
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function stageBadge(stage: 1 | 2 | 3): React.ReactElement {
  const map: Record<number, { label: string; className: string }> = {
    1: { label: 'Stage 1', className: 'bg-blue-100 text-blue-700' },
    2: { label: 'Stage 2', className: 'bg-indigo-100 text-indigo-700' },
    3: { label: 'Stage 3', className: 'bg-purple-100 text-purple-700' },
  }
  const { label, className } = map[stage] ?? { label: `Stage ${stage}`, className: 'bg-gray-100 text-gray-600' }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${className}`}>
      {label}
    </span>
  )
}

function crisisScoreBadge(score: number): React.ReactElement {
  let className = 'bg-green-100 text-green-700'
  let label = 'Low'
  if (score >= 0.7) {
    className = 'bg-red-100 text-red-700'
    label = 'High'
  } else if (score >= 0.3) {
    className = 'bg-amber-100 text-amber-700'
    label = 'Moderate'
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${className}`}>
      Crisis: {label} ({score.toFixed(2)})
    </span>
  )
}

function statusBadge(status: string): React.ReactElement {
  const map: Record<string, string> = {
    completed: 'bg-green-50 text-green-600',
    in_progress: 'bg-yellow-50 text-yellow-700',
    crisis_escalated: 'bg-red-50 text-red-700',
    pending: 'bg-gray-50 text-gray-500',
  }
  const className = map[status] ?? 'bg-gray-50 text-gray-500'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs capitalize ${className}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

// ─── SessionMessagePreview (mounted only when expanded) ───────────────────────

function SessionMessagePreview({ sessionId }: { sessionId: string }): React.ReactElement {
  const { messages, loading, error } = useSessionMessages(sessionId)

  if (loading) {
    return (
      <div className="mt-3 space-y-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-3 bg-gray-100 rounded w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return <p className="mt-3 text-xs text-red-500">{error}</p>
  }

  if (messages.length === 0) {
    return <p className="mt-3 text-xs text-gray-400 italic">No messages recorded for this session.</p>
  }

  // Show first 4 messages as a preview
  const preview: ChatMessage[] = messages.slice(0, 4)

  return (
    <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
      {preview.map((msg) => (
        <div
          key={msg.id}
          className={`flex gap-2 text-xs ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <span
            className={`px-2 py-1 rounded-lg max-w-xs truncate ${
              msg.role === 'user'
                ? 'bg-indigo-100 text-indigo-800'
                : 'bg-gray-100 text-gray-700'
            }`}
          >
            {msg.content}
          </span>
        </div>
      ))}
      {messages.length > 4 && (
        <p className="text-xs text-gray-400 text-center">
          +{messages.length - 4} more messages
        </p>
      )}
    </div>
  )
}

// ─── SessionCard ──────────────────────────────────────────────────────────────

function SessionCard({ session }: { session: TherapySession }): React.ReactElement {
  const [expanded, setExpanded] = useState(false)

  const startedAt = session.startedAt
    ? format(new Date(session.startedAt), 'dd MMM yyyy, h:mm a')
    : '—'

  return (
    <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-hidden">
      <button
        className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-300"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-800">{startedAt}</span>
            {stageBadge(session.stage)}
            {statusBadge(session.status)}
          </div>
          <div className="flex items-center gap-2">
            {crisisScoreBadge(session.crisisScore)}
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          <SessionMessagePreview sessionId={session.id} />
        </div>
      )}
    </div>
  )
}

// ─── SessionsTab ──────────────────────────────────────────────────────────────

function SessionsTab({ patientId }: { patientId: string }): React.ReactElement {
  const { sessions, loading, error, refetch } = usePatientSessions(patientId)

  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-white rounded-lg border border-gray-100" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-sm text-red-700 mb-2">{error}</p>
        <button
          onClick={refetch}
          className="text-sm text-red-600 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </div>
        <p className="text-gray-500 font-medium">No sessions yet</p>
        <p className="text-gray-400 text-sm mt-1">Your therapy sessions will appear here once started.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {sessions.map((session) => (
        <SessionCard key={session.id} session={session} />
      ))}
    </div>
  )
}

// ─── PatientPortal ────────────────────────────────────────────────────────────

export function PatientPortal() {
  const [activeTab, setActiveTab] = useState<'sessions' | 'assessments' | 'appointments'>('sessions')
  const [activeAssessment, setActiveAssessment] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [responses, setResponses] = useState<Record<number, number>>({})
  const [result, setResult] = useState<AssessmentResult | null>(null)
  const [loadingQuestions, setLoadingQuestions] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const patientId = localStorage.getItem('patient_id') || 'anonymous'

  const openAssessment = async (type: string) => {
    setActiveAssessment(type)
    setResponses({})
    setResult(null)
    setLoadingQuestions(true)
    try {
      const res = await getAssessmentQuestions(type)
      setQuestions(res.data.questions || [])
    } catch (err) {
      console.error('Failed to load questions:', err)
    } finally {
      setLoadingQuestions(false)
    }
  }

  const handleSubmit = async () => {
    if (!activeAssessment) return
    const orderedResponses = questions.map((q) => responses[q.id] ?? 0)
    setSubmitting(true)
    try {
      const res = await submitAssessment(patientId, {
        assessment_type: activeAssessment,
        responses: orderedResponses,
      })
      setResult(res.data.result)
    } catch (err) {
      console.error('Failed to submit assessment:', err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-indigo-50">
      <header className="bg-indigo-600 px-6 py-4">
        <h1 className="text-xl font-bold text-white">Your Wellness Journey</h1>
        <p className="text-indigo-200 text-sm">Powered by Saathi AI</p>
      </header>

      <div className="px-6 py-4 bg-white border-b">
        {(['sessions', 'assessments', 'appointments'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); setActiveAssessment(null); setResult(null) }}
            className={`mr-6 pb-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === tab ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <main className="px-6 py-6">
        {activeTab === 'sessions' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Your Sessions</h2>
            <SessionsTab patientId={patientId} />
          </div>
        )}

        {activeTab === 'assessments' && !activeAssessment && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Clinical Assessments</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {['PHQ-9', 'GAD-7', 'PCL-5', 'ISI', 'OCI-R', 'SPIN', 'PSS', 'WHO-5'].map((type) => (
                <button
                  key={type}
                  onClick={() => openAssessment(type)}
                  className="bg-white rounded-lg shadow-sm p-4 text-center border border-gray-100 hover:border-indigo-300 transition-colors"
                >
                  <p className="font-bold text-indigo-600 text-lg">{type}</p>
                  <p className="text-xs text-gray-500 mt-1">Take assessment</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'assessments' && activeAssessment && !result && (
          <div>
            <div className="flex items-center mb-4 gap-3">
              <button
                onClick={() => { setActiveAssessment(null); setQuestions([]) }}
                className="text-sm text-indigo-600 hover:underline"
              >
                &larr; Back
              </button>
              <h2 className="text-lg font-semibold text-gray-700">{activeAssessment} Assessment</h2>
            </div>

            {loadingQuestions ? (
              <p className="text-gray-400 text-sm">Loading questions...</p>
            ) : (
              <div className="space-y-6 max-w-2xl">
                {questions.map((q) => (
                  <div key={q.id} className="bg-white rounded-lg p-4 border border-gray-100">
                    <p className="text-sm font-medium text-gray-800 mb-3">{q.id + 1}. {q.text}</p>
                    <div className="flex gap-2 flex-wrap">
                      {q.scale.map((val, i) => (
                        <button
                          key={val}
                          onClick={() => setResponses((prev) => ({ ...prev, [q.id]: val }))}
                          className={`px-3 py-1.5 rounded text-xs border transition-colors ${
                            responses[q.id] === val
                              ? 'bg-indigo-600 text-white border-indigo-600'
                              : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
                          }`}
                        >
                          {val} — {q.labels[i]}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}

                {questions.length > 0 && (
                  <button
                    onClick={handleSubmit}
                    disabled={submitting || Object.keys(responses).length < questions.length}
                    className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-indigo-700 transition-colors"
                  >
                    {submitting ? 'Submitting...' : 'Submit Assessment'}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'assessments' && result && (
          <div className="max-w-md">
            <h2 className="text-lg font-semibold text-gray-700 mb-4">{result.assessment_type} Results</h2>
            <div className="bg-white rounded-lg p-6 border border-gray-100 shadow-sm">
              <p className="text-3xl font-bold text-indigo-600 mb-1">{result.total_score}</p>
              <p className="text-sm text-gray-500 mb-3">out of {result.max_possible}</p>
              <p className="text-lg font-medium text-gray-800">Severity: <span className="text-indigo-700">{result.severity}</span></p>
            </div>
            <button
              onClick={() => { setActiveAssessment(null); setResult(null) }}
              className="mt-4 text-sm text-indigo-600 hover:underline"
            >
              Take another assessment
            </button>
          </div>
        )}

        {activeTab === 'appointments' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Appointments</h2>
            <p className="text-gray-400 text-sm">Your upcoming appointments will appear here.</p>
          </div>
        )}
      </main>
    </div>
  )
}
