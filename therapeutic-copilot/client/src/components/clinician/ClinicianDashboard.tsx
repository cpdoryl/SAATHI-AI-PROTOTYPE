/**
 * SAATHI AI — Clinician Dashboard
 * Main hub for: patient overview, crisis alerts, session monitoring, analytics.
 */
import React, { useState, useEffect } from 'react'
import { Patient, CrisisAlert } from '@/types'
import { listLeads } from '@/lib/api'

export function ClinicianDashboard() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [crisisAlerts, setCrisisAlerts] = useState<CrisisAlert[]>([])
  const [activeTab, setActiveTab] = useState<'patients' | 'alerts' | 'analytics'>('patients')

  useEffect(() => {
    // Connect to clinician WebSocket for real-time alerts
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
            {patients.length === 0 ? (
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

        {activeTab === 'analytics' && (
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">Analytics</h2>
            <p className="text-gray-400 text-sm">Charts and metrics coming soon.</p>
          </div>
        )}
      </main>
    </div>
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
