/**
 * SAATHI AI — Analytics Dashboard
 * Key metrics: sessions, assessment scores, crisis events, dropout rates.
 */
import React from 'react'

const MOCK_STATS = [
  { label: 'Active Patients', value: '—', sub: 'this month' },
  { label: 'Sessions Completed', value: '—', sub: 'this month' },
  { label: 'Crisis Events', value: '—', sub: 'last 30 days' },
  { label: 'Avg PHQ-9 Score', value: '—', sub: 'all patients' },
]

export function Analytics() {
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {MOCK_STATS.map(({ label, value, sub }) => (
          <div key={label} className="bg-white rounded-xl shadow-sm border p-5">
            <p className="text-sm text-gray-500">{label}</p>
            <p className="text-3xl font-bold text-indigo-600 mt-1">{value}</p>
            <p className="text-xs text-gray-400 mt-1">{sub}</p>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="font-semibold text-gray-700 mb-4">Patient Assessment Trends</h3>
        <p className="text-gray-400 text-sm">Charts will render here (Recharts integration in progress).</p>
      </div>
    </div>
  )
}
