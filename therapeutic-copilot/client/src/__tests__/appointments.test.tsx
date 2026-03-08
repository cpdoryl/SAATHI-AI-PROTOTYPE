/**
 * SAATHI AI — Appointments Tab tests
 * Uses Vitest + React Testing Library + vi.mock for API isolation.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// ─── Mock Recharts (ClinicianDashboard imports Recharts) ──────────────────────

vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// ─── Mock API ─────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  listPatients: vi.fn(),
  getAnalyticsSummary: vi.fn(),
  listAppointments: vi.fn(),
  createAppointment: vi.fn(),
  cancelAppointment: vi.fn(),
}))

import * as api from '@/lib/api'
import { ClinicianDashboard } from '@/components/clinician/ClinicianDashboard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_APPOINTMENTS = [
  {
    id: 'appt-1',
    patientId: 'patient-abc',
    clinicianId: 'clinician-xyz',
    scheduledAt: '2026-03-10T10:00:00.000Z',
    durationMinutes: 60,
    status: 'scheduled',
    amountInr: 1500,
    paymentStatus: 'pending',
  },
  {
    id: 'appt-2',
    patientId: 'patient-def',
    clinicianId: 'clinician-xyz',
    scheduledAt: '2026-03-11T14:00:00.000Z',
    durationMinutes: 45,
    status: 'confirmed',
    amountInr: 1200,
    paymentStatus: 'paid',
  },
  {
    id: 'appt-3',
    patientId: 'patient-ghi',
    clinicianId: 'clinician-xyz',
    scheduledAt: '2026-03-08T09:00:00.000Z',
    durationMinutes: 60,
    status: 'cancelled',
    amountInr: 1500,
    paymentStatus: 'refunded',
  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function switchToAppointmentsTab() {
  const btn = screen.getByRole('button', { name: /appointments/i })
  fireEvent.click(btn)
}

// ─── Setup ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.stubGlobal('WebSocket', class {
    onmessage = null
    close = vi.fn()
  })
  localStorage.setItem('clinician_id', 'clinician-xyz')
  ;(api.listPatients as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { patients: [] } })
  ;(api.getAnalyticsSummary as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} })
  ;(api.listAppointments as ReturnType<typeof vi.fn>).mockResolvedValue({
    data: { appointments: MOCK_APPOINTMENTS },
  })
  ;(api.createAppointment as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} })
  ;(api.cancelAppointment as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} })
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ClinicianDashboard — Appointments tab', () => {
  it('renders the Appointments tab button', () => {
    render(<ClinicianDashboard />)
    expect(screen.getByRole('button', { name: /appointments/i })).toBeInTheDocument()
  })

  it('calls listAppointments on mount when tab is switched', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()
    await waitFor(() => {
      expect(api.listAppointments).toHaveBeenCalledTimes(1)
    })
  })

  it('renders appointment list rows from API', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getByText(/patient-abc/i)).toBeInTheDocument()
      expect(screen.getByText(/patient-def/i)).toBeInTheDocument()
    })
  })

  it('shows loading spinner while fetching', async () => {
    let resolve: (v: unknown) => void
    ;(api.listAppointments as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((r) => { resolve = r })
    )
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    resolve!({ data: { appointments: [] } })
  })

  it('shows error state when listAppointments fails', async () => {
    ;(api.listAppointments as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'))
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getByText(/failed to load appointments/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('shows empty state when no appointments', async () => {
    ;(api.listAppointments as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { appointments: [] },
    })
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getByText(/no appointments yet/i)).toBeInTheDocument()
    })
  })

  it('opens Create Appointment form on button click', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()
    await waitFor(() => screen.getByText(/\+ new appointment/i))

    fireEvent.click(screen.getByText(/\+ new appointment/i))
    expect(screen.getByText('Create Appointment')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/enter patient uuid/i)).toBeInTheDocument()
  })

  it('shows inline validation error when patientId is empty on submit', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()
    await waitFor(() => screen.getByText(/\+ new appointment/i))

    fireEvent.click(screen.getByText(/\+ new appointment/i))
    fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(screen.getByText(/patient id is required/i)).toBeInTheDocument()
    })
    expect(api.createAppointment).not.toHaveBeenCalled()
  })

  it('calls createAppointment with correct payload on valid submit', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()
    await waitFor(() => screen.getByText(/\+ new appointment/i))

    fireEvent.click(screen.getByText(/\+ new appointment/i))

    fireEvent.change(screen.getByPlaceholderText(/enter patient uuid/i), {
      target: { value: 'patient-new' },
    })
    fireEvent.change(screen.getByDisplayValue(''), {
      target: { value: '2026-03-15T11:00' },
    })

    fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(api.createAppointment).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_id: 'patient-new',
          clinician_id: 'clinician-xyz',
        })
      )
    })
  })

  it('Cancel button calls cancelAppointment for scheduled appointment', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /cancel/i }).length).toBeGreaterThan(0)
    })

    vi.stubGlobal('confirm', () => true)
    const cancelBtns = screen.getAllByRole('button', { name: /^cancel$/i })
    fireEvent.click(cancelBtns[0])

    await waitFor(() => {
      expect(api.cancelAppointment).toHaveBeenCalledWith('appt-1')
    })
  })

  it('does not show Cancel button for cancelled appointment', async () => {
    ;(api.listAppointments as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { appointments: [MOCK_APPOINTMENTS[2]] }, // status: 'cancelled'
    })
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getByText(/patient-ghi/i)).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /^cancel$/i })).not.toBeInTheDocument()
  })

  it('renders the weekly calendar navigation', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /previous week/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /next week/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /today/i })).toBeInTheDocument()
    })
  })

  it('renders all 7 day column headers in the calendar', async () => {
    render(<ClinicianDashboard />)
    switchToAppointmentsTab()

    await waitFor(() => {
      expect(screen.getByText('Mon')).toBeInTheDocument()
      expect(screen.getByText('Tue')).toBeInTheDocument()
      expect(screen.getByText('Sat')).toBeInTheDocument()
      expect(screen.getByText('Sun')).toBeInTheDocument()
    })
  })
})

// ─── Unit tests for appointments API functions ────────────────────────────────

describe('Appointments API functions', () => {
  it('listAppointments returns appointments array', async () => {
    ;(api.listAppointments as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { appointments: MOCK_APPOINTMENTS },
    })
    const result = await api.listAppointments()
    expect(result.data.appointments).toHaveLength(3)
    expect(result.data.appointments[0].id).toBe('appt-1')
  })

  it('createAppointment sends POST with payload', async () => {
    const payload = {
      patient_id: 'p1',
      clinician_id: 'c1',
      scheduled_at: '2026-03-20T10:00:00Z',
      duration_minutes: 60,
      amount_inr: 1500,
    }
    ;(api.createAppointment as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { id: 'new-appt' } })
    const result = await api.createAppointment(payload)
    expect(result.data.id).toBe('new-appt')
  })

  it('cancelAppointment sends PUT to correct endpoint', async () => {
    ;(api.cancelAppointment as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { status: 'cancelled' } })
    const result = await api.cancelAppointment('appt-1')
    expect(result.data.status).toBe('cancelled')
    expect(api.cancelAppointment).toHaveBeenCalledWith('appt-1')
  })
})
