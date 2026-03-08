/**
 * SAATHI AI — ClinicianDashboard tests
 * Covers: patient list rendering, RiskBadge color logic.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// ─── Mock API + WebSocket ─────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  listPatients: vi.fn(),
  getAnalyticsSummary: vi.fn(),
  listAppointments: vi.fn(),
  createAppointment: vi.fn(),
  cancelAppointment: vi.fn(),
}))

// Prevent real WebSocket connections in tests
const mockWsInstance = { onmessage: null as unknown, close: vi.fn() }
vi.stubGlobal('WebSocket', vi.fn(() => mockWsInstance))

import * as api from '@/lib/api'
import { ClinicianDashboard } from '@/components/clinician/ClinicianDashboard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const makePatient = (overrides = {}) => ({
  id: 'p1',
  fullName: 'Test Patient',
  stage: 'active' as const,
  dropoutRiskScore: 0.5,
  lastActive: '2026-03-01T10:00:00Z',
  language: 'en',
  ...overrides,
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ClinicianDashboard — Patients tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    vi.mocked(api.listPatients).mockReturnValue(new Promise(() => {}))
    render(<ClinicianDashboard />)
    expect(screen.getByText(/loading patients/i)).toBeDefined()
  })

  it('renders empty state when no patients', async () => {
    vi.mocked(api.listPatients).mockResolvedValue({ data: { patients: [] } } as never)
    render(<ClinicianDashboard />)
    await waitFor(() => {
      expect(screen.getByText(/no patients yet/i)).toBeDefined()
    })
  })

  it('renders patient card with patient name', async () => {
    vi.mocked(api.listPatients).mockResolvedValue({
      data: { patients: [makePatient({ fullName: 'Aryan Sharma' })] },
    } as never)
    render(<ClinicianDashboard />)
    await waitFor(() => {
      expect(screen.getByText('Aryan Sharma')).toBeDefined()
    })
  })

  it('shows red risk badge when dropoutRiskScore > 0.7', async () => {
    vi.mocked(api.listPatients).mockResolvedValue({
      data: { patients: [makePatient({ dropoutRiskScore: 0.85 })] },
    } as never)
    render(<ClinicianDashboard />)
    await waitFor(() => {
      const badge = screen.getByText('85% risk')
      expect(badge.className).toContain('bg-red-100')
      expect(badge.className).toContain('text-red-700')
    })
  })

  it('shows yellow risk badge when dropoutRiskScore is 0.3–0.7', async () => {
    vi.mocked(api.listPatients).mockResolvedValue({
      data: { patients: [makePatient({ dropoutRiskScore: 0.5 })] },
    } as never)
    render(<ClinicianDashboard />)
    await waitFor(() => {
      const badge = screen.getByText('50% risk')
      expect(badge.className).toContain('bg-yellow-100')
      expect(badge.className).toContain('text-yellow-700')
    })
  })

  it('shows green risk badge when dropoutRiskScore < 0.3', async () => {
    vi.mocked(api.listPatients).mockResolvedValue({
      data: { patients: [makePatient({ dropoutRiskScore: 0.1 })] },
    } as never)
    render(<ClinicianDashboard />)
    await waitFor(() => {
      const badge = screen.getByText('10% risk')
      expect(badge.className).toContain('bg-green-100')
      expect(badge.className).toContain('text-green-700')
    })
  })
})
