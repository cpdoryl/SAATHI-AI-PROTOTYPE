/**
 * SAATHI AI — Patient Portal
 * Patient-facing interface for session history, assessments, and appointments.
 */
import React, { useState } from 'react'

export function PatientPortal() {
  const [activeTab, setActiveTab] = useState<'sessions' | 'assessments' | 'appointments'>('sessions')

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
            onClick={() => setActiveTab(tab)}
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

        {activeTab === 'assessments' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Clinical Assessments</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {['PHQ-9', 'GAD-7', 'PCL-5', 'ISI', 'OCI-R', 'SPIN', 'PSS', 'WHO-5'].map((type) => (
                <button
                  key={type}
                  className="bg-white rounded-lg shadow-sm p-4 text-center border border-gray-100 hover:border-indigo-300 transition-colors"
                >
                  <p className="font-bold text-indigo-600 text-lg">{type}</p>
                  <p className="text-xs text-gray-500 mt-1">Take assessment</p>
                </button>
              ))}
            </div>
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
