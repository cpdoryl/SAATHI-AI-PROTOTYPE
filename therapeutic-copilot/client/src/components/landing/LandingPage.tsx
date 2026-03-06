/**
 * SAATHI AI — Landing Page
 * Marketing page for B2B clinic sign-up.
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'

export function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-white">
      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-5 bg-white shadow-sm">
        <div className="text-2xl font-bold text-indigo-600">Saathi AI</div>
        <div className="flex items-center space-x-6">
          <a href="#features" className="text-gray-600 hover:text-indigo-600 text-sm">Features</a>
          <a href="#pricing" className="text-gray-600 hover:text-indigo-600 text-sm">Pricing</a>
          <button onClick={() => navigate('/login')} className="text-indigo-600 text-sm font-medium">Login</button>
          <button onClick={() => navigate('/signup')} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-8 py-24 text-center max-w-4xl mx-auto">
        <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
          AI-Powered Therapeutic Co-Pilot<br />
          <span className="text-indigo-600">for Mental Health Clinics</span>
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          Embed Saathi AI on your clinic website in 30 seconds. Convert visitors into patients,
          deliver 24/7 therapeutic support, and get real-time crisis alerts.
        </p>
        <div className="flex justify-center space-x-4">
          <button className="bg-indigo-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-indigo-700">
            Start Free Trial
          </button>
          <button className="border border-indigo-600 text-indigo-600 px-8 py-3 rounded-lg font-semibold hover:bg-indigo-50">
            Book a Demo
          </button>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-8 py-20 bg-white">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">Simple, Transparent Pricing</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {[
            { plan: 'Basic', price: '₹2,999', desc: 'Solo practitioner', features: ['1 Clinician', 'Widget embed', 'AI Chat', 'Basic analytics'] },
            { plan: 'Professional', price: '₹9,999', desc: '2–5 clinicians', features: ['5 Clinicians', 'All Basic features', 'Crisis alerts', 'RAG knowledge base', 'Razorpay payments'] },
            { plan: 'Enterprise', price: 'Custom', desc: '5+ clinicians', features: ['Unlimited clinicians', 'All Pro features', 'SLA guarantee', 'Dedicated support', 'Custom AI training'] },
          ].map(({ plan, price, desc, features }) => (
            <div key={plan} className={`rounded-2xl p-8 border-2 ${plan === 'Professional' ? 'border-indigo-600 shadow-lg' : 'border-gray-200'}`}>
              <h3 className="text-xl font-bold text-gray-900">{plan}</h3>
              <p className="text-gray-500 text-sm mb-4">{desc}</p>
              <div className="text-3xl font-bold text-indigo-600 mb-6">{price}<span className="text-base font-normal text-gray-500">/mo</span></div>
              <ul className="space-y-2">
                {features.map((f) => (
                  <li key={f} className="flex items-center text-sm text-gray-600">
                    <span className="text-green-500 mr-2">✓</span>{f}
                  </li>
                ))}
              </ul>
              <button className={`w-full mt-8 py-2 rounded-lg font-medium text-sm ${plan === 'Professional' ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'border border-indigo-600 text-indigo-600 hover:bg-indigo-50'}`}>
                {plan === 'Enterprise' ? 'Contact Sales' : 'Get Started'}
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
