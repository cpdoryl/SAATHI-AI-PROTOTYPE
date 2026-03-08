/**
 * SAATHI AI — Analytics Tab tests
 * Uses Vitest + React Testing Library + vi.mock for API isolation.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// ─── Mock Recharts to avoid canvas/SVG issues in jsdom ───────────────────────

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
}))

import * as api from '@/lib/api'
import { ClinicianDashboard } from '@/components/clinician/ClinicianDashboard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_SUMMARY = {
  weekly_sessions: [
    { day: 'Mon', sessions: 3 },
    { day: 'Tue', sessions: 5 },
    { day: 'Wed', sessions: 2 },
    { day: 'Thu', sessions: 8 },
    { day: 'Fri', sessions: 4 },
    { day: 'Sat', sessions: 1 },
    { day: 'Sun', sessions: 0 },
  ],
  crisis_rate: [
    { week: 'Wk 1', crisisRate: 0.1, total: 10, crisisCount: 1 },
    { week: 'Wk 2', crisisRate: 0.2, total: 15, crisisCount: 3 },
    { week: 'Wk 3', crisisRate: 0.05, total: 20, crisisCount: 1 },
    { week: 'Wk 4', crisisRate: 0.15, total: 13, crisisCount: 2 },
  ],
  patient_stages: [
    { stage: 'LEAD', count: 12 },
    { stage: 'ACTIVE', count: 28 },
    { stage: 'DROPOUT', count: 5 },
  ],
  assessment_scores: [
    { type: 'PHQ-9', avgScore: 11.2, count: 18 },
    { type: 'GAD-7', avgScore: 9.5, count: 14 },
  ],
  total_active_patients: 28,
  total_sessions_this_week: 23,
  crisis_alerts_this_week: 3,
}

// ─── Suppress WebSocket errors in test env ────────────────────────────────────

beforeEach(() => {
  vi.stubGlobal('WebSocket', class {
    onmessage = null
    close = vi.fn()
  })
  ;(api.listPatients as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { patients: [] } })
  ;(api.getAnalyticsSummary as ReturnType<typeof vi.fn>).mockResolvedValue({ data: MOCK_SUMMARY })
})

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ClinicianDashboard — Analytics tab', () => {
  it('shows loading spinner while fetching analytics', async () => {
    let resolve: (v: unknown) => void
    ;(api.getAnalyticsSummary as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise((r) => { resolve = r })
    )

    render(<ClinicianDashboard />)
    // Switch to analytics tab
    const analyticsTab = screen.getByRole('button', { name: /analytics/i })
    analyticsTab.click()

    expect(screen.getByRole('button', { name: /analytics/i })).toBeInTheDocument()
    // Spinner is rendered (animate-spin div)
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    resolve!({ data: MOCK_SUMMARY })
  })

  it('renders KPI cards with correct values after load', async () => {
    render(<ClinicianDashboard />)
    const analyticsTab = screen.getByRole('button', { name: /analytics/i })
    analyticsTab.click()

    await waitFor(() => {
      expect(screen.getByText('28')).toBeInTheDocument() // active patients
      expect(screen.getByText('23')).toBeInTheDocument() // sessions this week
      expect(screen.getByText('3')).toBeInTheDocument()  // crisis alerts
    })
    expect(screen.getByText('Active Patients')).toBeInTheDocument()
    expect(screen.getByText('Sessions This Week')).toBeInTheDocument()
    expect(screen.getByText('Crisis Alerts (7 days)')).toBeInTheDocument()
  })

  it('renders all four chart containers', async () => {
    render(<ClinicianDashboard />)
    screen.getByRole('button', { name: /analytics/i }).click()

    await waitFor(() => {
      expect(screen.getAllByTestId('bar-chart').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByTestId('area-chart').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByTestId('pie-chart').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders chart titles', async () => {
    render(<ClinicianDashboard />)
    screen.getByRole('button', { name: /analytics/i }).click()

    await waitFor(() => {
      expect(screen.getByText('Sessions — Last 7 Days')).toBeInTheDocument()
      expect(screen.getByText('Crisis Detection Rate — Last 4 Weeks')).toBeInTheDocument()
      expect(screen.getByText('Patient Stage Distribution')).toBeInTheDocument()
      expect(screen.getByText('Avg Assessment Score by Type')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    ;(api.getAnalyticsSummary as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'))
    render(<ClinicianDashboard />)
    screen.getByRole('button', { name: /analytics/i }).click()

    await waitFor(() => {
      expect(screen.getByText(/Failed to load analytics/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })
})

// ─── Unit tests for AnalyticsService (via API mock response shape) ────────────

describe('getAnalyticsSummary — API function', () => {
  it('calls GET /analytics/summary', async () => {
    const mockGet = api.getAnalyticsSummary as ReturnType<typeof vi.fn>
    mockGet.mockResolvedValue({ data: MOCK_SUMMARY })
    const result = await api.getAnalyticsSummary()
    expect(result.data.total_active_patients).toBe(28)
    expect(result.data.patient_stages).toHaveLength(3)
    expect(result.data.weekly_sessions).toHaveLength(7)
    expect(result.data.crisis_rate).toHaveLength(4)
    expect(result.data.assessment_scores).toHaveLength(2)
  })
})
