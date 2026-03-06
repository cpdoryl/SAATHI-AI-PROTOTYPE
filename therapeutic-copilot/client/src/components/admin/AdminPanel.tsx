/**
 * SAATHI AI — Admin Panel
 * Super-admin view: tenant management, system health, billing.
 */
import React from 'react'

export function AdminPanel() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Admin Panel</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {['Tenants', 'System Health', 'Billing'].map((section) => (
          <div key={section} className="bg-white rounded-xl shadow-sm border p-5">
            <h3 className="font-semibold text-gray-700">{section}</h3>
            <p className="text-gray-400 text-sm mt-2">Configure {section.toLowerCase()} settings.</p>
          </div>
        ))}
      </div>
    </div>
  )
}
