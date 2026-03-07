/**
 * SAATHI AI — Patient Portal
 * Patient-facing interface for session history, assessments, and appointments.
 */
import React, { useState } from 'react'
import { getAssessmentQuestions, submitAssessment } from '@/lib/api'

type Question = { id: number; text: string; scale: number[]; labels: string[] }
type AssessmentResult = { assessment_type: string; total_score: number; severity: string; max_possible: number }

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
            <p className="text-gray-400 text-sm">Your therapy session history will appear here.</p>
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
