/**
 * SAATHI AI — Landing Page
 * Marketing page for B2B clinic sign-up.
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'

const HOW_IT_WORKS_STEPS = [
  {
    step: '01',
    title: 'Embed in 30 Seconds',
    description:
      'Copy a single <script> tag into your clinic website. Saathi AI appears as a branded chat bubble — no coding required.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  },
  {
    step: '02',
    title: 'AI Engages Your Patients',
    description:
      'Saathi guides patients through validated assessments (PHQ-9, GAD-7, PCL-5), delivers evidence-based therapeutic conversations, and detects crisis signals in real time.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    step: '03',
    title: 'You Stay in Control',
    description:
      'Your clinician dashboard shows real-time crisis alerts, patient progress, dropout risk scores, and session analytics. You decide when to step in.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
]

const FEATURES = [
  {
    title: '24/7 Therapeutic Support',
    description: 'AI conversations guided by CBT, DBT, and mindfulness protocols — available round the clock so patients are never left waiting.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: 'Real-Time Crisis Detection',
    description: 'Monitors 30+ distress signals with sub-100ms latency. Clinicians receive instant WebSocket alerts before a situation escalates.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
  {
    title: 'Validated Assessments',
    description: 'PHQ-9, GAD-7, PCL-5, AUDIT, DAST, and more — automatically scored and tracked over time to measure patient progress.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
  {
    title: 'Dropout Risk Prediction',
    description: 'ML-powered risk scores flag patients likely to disengage. Reach out proactively before they drop out of care.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
  },
  {
    title: 'Seamless Payments',
    description: 'Integrated Razorpay checkout for appointment booking. Patients pay in seconds; clinicians get paid on time.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
      </svg>
    ),
  },
  {
    title: 'HIPAA-Ready Infrastructure',
    description: 'End-to-end encryption, per-tenant data isolation, and audit logs baked in. Built for healthcare compliance from day one.',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
]

const PRICING_PLANS = [
  {
    plan: 'Basic',
    price: '₹2,999',
    desc: 'Solo practitioner',
    features: ['1 Clinician seat', 'Widget embed', 'AI therapeutic chat', 'Basic analytics dashboard', 'Email support'],
    highlight: false,
    cta: 'Get Started',
  },
  {
    plan: 'Pro',
    price: '₹7,999',
    desc: '2–5 clinicians',
    features: ['5 Clinician seats', 'All Basic features', 'Real-time crisis alerts', 'RAG knowledge base', 'Razorpay payments', 'Priority support'],
    highlight: true,
    cta: 'Get Started',
  },
  {
    plan: 'Enterprise',
    price: 'Custom',
    desc: '5+ clinicians',
    features: ['Unlimited clinician seats', 'All Pro features', 'SLA guarantee', 'Dedicated account manager', 'Custom AI model training', 'On-premise deployment option'],
    highlight: false,
    cta: 'Contact Sales',
  },
]

const FOOTER_LINKS = {
  Product: ['Features', 'Pricing', 'Security', 'Changelog'],
  Company: ['About', 'Blog', 'Careers', 'Contact'],
  Legal: ['Privacy Policy', 'Terms of Service', 'HIPAA Compliance'],
  Support: ['Documentation', 'API Reference', 'Status', 'Help Center'],
}

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-white font-sans">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-8 py-4 bg-white/90 backdrop-blur-sm shadow-sm">
        <div className="text-2xl font-bold text-indigo-600">Saathi AI</div>
        <div className="hidden md:flex items-center space-x-8">
          <a href="#features" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">Features</a>
          <a href="#how-it-works" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">How It Works</a>
          <a href="#pricing" className="text-gray-600 hover:text-indigo-600 text-sm transition-colors">Pricing</a>
        </div>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/login')}
            className="text-indigo-600 text-sm font-medium hover:text-indigo-700 transition-colors"
          >
            Login
          </button>
          <button
            onClick={() => navigate('/register')}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-8 py-24 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center bg-indigo-50 text-indigo-700 text-xs font-semibold px-3 py-1 rounded-full mb-6">
          Trusted by mental health clinics across India
        </div>
        <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
          AI-Powered Therapeutic Co-Pilot<br />
          <span className="text-indigo-600">for Mental Health Clinics</span>
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
          Embed Saathi AI on your clinic website in 30 seconds. Convert visitors into patients,
          deliver 24/7 therapeutic support, and get real-time crisis alerts.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-4">
          <button
            onClick={() => navigate('/register')}
            className="bg-indigo-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Start Free Trial
          </button>
          <button className="border border-indigo-600 text-indigo-600 px-8 py-3 rounded-lg font-semibold hover:bg-indigo-50 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
            Book a Demo
          </button>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-8 py-20 max-w-6xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Everything your clinic needs</h2>
          <p className="text-gray-500 max-w-xl mx-auto">
            A complete mental-health-tech stack — from patient engagement to compliance — so you can focus on care.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {FEATURES.map(({ title, description, icon }) => (
            <div
              key={title}
              className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-4">
                {icon}
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="px-8 py-20 bg-indigo-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">How It Works</h2>
            <p className="text-gray-500 max-w-xl mx-auto">
              From installation to your first patient interaction — in under five minutes.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Connector line — desktop only */}
            <div className="hidden md:block absolute top-10 left-1/6 right-1/6 h-0.5 bg-indigo-200" style={{ left: '16.67%', right: '16.67%' }} />
            {HOW_IT_WORKS_STEPS.map(({ step, title, description, icon }, idx) => (
              <div key={step} className="relative flex flex-col items-center text-center">
                {/* Step number bubble */}
                <div className="relative z-10 w-20 h-20 bg-indigo-600 text-white rounded-full flex flex-col items-center justify-center mb-6 shadow-md">
                  {icon}
                </div>
                <div className="absolute -top-2 -right-2 z-20 w-6 h-6 bg-white border-2 border-indigo-600 text-indigo-600 rounded-full flex items-center justify-center text-xs font-bold">
                  {idx + 1}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-12">
            <button
              onClick={() => navigate('/register')}
              className="bg-indigo-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Get Started Free
            </button>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-8 py-20 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Simple, Transparent Pricing</h2>
            <p className="text-gray-500 max-w-xl mx-auto">
              No hidden fees. Cancel anytime. All plans include a 14-day free trial.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {PRICING_PLANS.map(({ plan, price, desc, features, highlight, cta }) => (
              <div
                key={plan}
                className={`relative rounded-2xl p-8 border-2 flex flex-col ${
                  highlight
                    ? 'border-indigo-600 shadow-xl'
                    : 'border-gray-200 shadow-sm'
                }`}
              >
                {highlight && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-semibold px-4 py-1 rounded-full">
                    Most Popular
                  </div>
                )}
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{plan}</h3>
                  <p className="text-gray-500 text-sm mb-4">{desc}</p>

                  <div className="flex items-end gap-1 mb-6">
                    <span className="text-4xl font-bold text-indigo-600">{price}</span>
                    {price !== 'Custom' && (
                      <span className="text-base font-normal text-gray-500 mb-1">/mo</span>
                    )}
                  </div>
                  <ul className="space-y-3 mb-8">
                    {features.map((f) => (
                      <li key={f} className="flex items-start text-sm text-gray-600">
                        <svg className="w-4 h-4 text-green-500 mr-2 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
                <button
                  onClick={() => plan !== 'Enterprise' && navigate('/register')}
                  className={`mt-auto w-full py-2.5 rounded-lg font-medium text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                    highlight
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                      : 'border border-indigo-600 text-indigo-600 hover:bg-indigo-50'
                  }`}
                >
                  {cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 px-8 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-10 mb-12">
            {/* Brand column */}
            <div className="lg:col-span-1">
              <div className="text-2xl font-bold text-white mb-3">Saathi AI</div>
              <p className="text-sm leading-relaxed mb-4">
                AI-powered therapeutic co-pilot for mental health clinics across India.
              </p>
              <p className="text-xs text-gray-500">
                RYL NEUROACADEMY<br />PRIVATE LIMITED
              </p>
            </div>

            {/* Link columns */}
            {Object.entries(FOOTER_LINKS).map(([category, links]) => (
              <div key={category}>
                <h4 className="text-white text-sm font-semibold mb-4">{category}</h4>
                <ul className="space-y-2">
                  {links.map((link) => (
                    <li key={link}>
                      <a
                        href="#"
                        className="text-sm hover:text-indigo-400 transition-colors"
                      >
                        {link}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Bottom bar */}
          <div className="border-t border-gray-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm">
              © {new Date().getFullYear()} RYL NEUROACADEMY PRIVATE LIMITED. All rights reserved.
            </p>
            <div className="flex items-center gap-6 text-sm">
              <a href="#" className="hover:text-indigo-400 transition-colors">Privacy</a>
              <a href="#" className="hover:text-indigo-400 transition-colors">Terms</a>
              <a href="#" className="hover:text-indigo-400 transition-colors">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
