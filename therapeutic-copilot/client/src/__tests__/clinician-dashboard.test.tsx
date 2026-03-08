/**
 * SAATHI AI — ClinicianDashboard tests
 * Covers: patient list rendering, RiskBadge color logic.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// ─── Mock API + WebSocket ─────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  listPatients: vi.fn(),
  getAnalyticsSummary: vi.fn(),
  listAppointments: vi.fn(),
  createAppointment: vi.fn(),
  cancelAppointment: vi.fn(),
  listPatientSessions: vi.fn(),
  getAssessmentHistory: vi.fn(),
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

// ─── Patient Detail Drawer tests ───────────────────────────────────────────────

describe('PatientDetailDrawer', () => {
  const patient = {
    id: 'p42',
    fullName: 'Priya Nair',
    stage: 'active' as const,
    dropoutRiskScore: 0.4,
    lastActive: '2026-03-01T10:00:00Z',
    language: 'hi',
    email: 'priya@test.com',
    phone: '9876543210',
  }

  const mockSessions = [
    {
      id: 's1',
      patientId: 'p42',
      stage: 1,
      currentStep: 3,
      status: 'completed',
      crisisScore: 0.1,
      startedAt: '2026-02-28T09:00:00Z',
    },
    {
      id: 's2',
      patientId: 'p42',
      stage: 2,
      currentStep: 1,
      status: 'in_progress',
      crisisScore: 0,
      startedAt: '2026-03-01T10:00:00Z',
    },
  ]

  const mockAssessments = [
    {
      id: 'a1',
      patientId: 'p42',
      assessmentType: 'phq9',
      score: 14,
      severity: 'moderate',
      administeredAt: '2026-02-25T08:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listPatients).mockResolvedValue({
      data: { patients: [patient] },
    } as never)
    vi.mocked(api.listPatientSessions).mockResolvedValue({
      data: { sessions: mockSessions },
    } as never)
    vi.mocked(api.getAssessmentHistory).mockResolvedValue({
      data: { assessments: mockAssessments },
    } as never)
  })

  it('opens drawer when a patient card is clicked', async () => {
    render(<ClinicianDashboard />)
    await waitFor(() => expect(screen.getByText('Priya Nair')).toBeDefined())

    fireEvent.click(screen.getByText('Priya Nair'))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined()
      expect(screen.getByText('Patient Details')).toBeDefined()
    })
  })

  it('drawer shows session count after loading', async () => {
    render(<ClinicianDashboard />)
    await waitFor(() => expect(screen.getByText('Priya Nair')).toBeDefined())

    fireEvent.click(screen.getByText('Priya Nair'))

    await waitFor(() => {
      expect(screen.getByText('Sessions')).toBeDefined()
      // session count kpi
      expect(screen.getByText('2')).toBeDefined()
    })
  })

  it('drawer shows last PHQ-9 score', async () => {
    render(<ClinicianDashboard />)
    await waitFor(() => expect(screen.getByText('Priya Nair')).toBeDefined())

    fireEvent.click(screen.getByText('Priya Nair'))

    await waitFor(() => {
      expect(screen.getByText('14')).toBeDefined()
      expect(screen.getByText('Last PHQ-9')).toBeDefined()
    })
  })

  it('drawer closes when close button is clicked', async () => {
    render(<ClinicianDashboard />)
    await waitFor(() => expect(screen.getByText('Priya Nair')).toBeDefined())

    fireEvent.click(screen.getByText('Priya Nair'))
    await waitFor(() => expect(screen.getByRole('dialog')).toBeDefined())

    fireEvent.click(screen.getByLabelText('Close drawer'))
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).toBeNull()
    })
  })

  it('drawer shows patient email and phone', async () => {
    render(<ClinicianDashboard />)
    await waitFor(() => expect(screen.getByText('Priya Nair')).toBeDefined())

    fireEvent.click(screen.getByText('Priya Nair'))

    await waitFor(() => {
      expect(screen.getByText('priya@test.com')).toBeDefined()
      expect(screen.getByText('9876543210')).toBeDefined()
    })
  })
})
