/**
 * SAATHI AI — Shared UI Primitives
 * Reusable components across all dashboards.
 */
import React from 'react'

// ─── Button ───────────────────────────────────────────────────────────────────

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({ variant = 'primary', size = 'md', className = '', ...props }: ButtonProps) {
  const base = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors disabled:opacity-50'
  const variants = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
    secondary: 'border border-indigo-600 text-indigo-600 hover:bg-indigo-50',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  }
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' }
  return <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props} />
}

// ─── Badge ────────────────────────────────────────────────────────────────────

interface BadgeProps { label: string; color?: 'green' | 'yellow' | 'red' | 'gray' | 'indigo' }
export function Badge({ label, color = 'gray' }: BadgeProps) {
  const colors = {
    green: 'bg-green-100 text-green-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    red: 'bg-red-100 text-red-800',
    gray: 'bg-gray-100 text-gray-600',
    indigo: 'bg-indigo-100 text-indigo-800',
  }
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[color]}`}>{label}</span>
}

// ─── Card ─────────────────────────────────────────────────────────────────────

export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white rounded-xl shadow-sm border border-gray-100 p-5 ${className}`}>{children}</div>
}

// ─── Spinner ─────────────────────────────────────────────────────────────────

export function Spinner() {
  return <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
}
