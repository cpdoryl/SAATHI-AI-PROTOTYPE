/**
 * SAATHI AI — PatientPortal & session-history hooks tests
 * Uses Vitest + React Testing Library + vi.mock for API isolation.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// ─── Mock API module before importing hooks ───────────────────────────────────

vi.mock('@/lib/api', () => ({
  listPatientSessions: vi.fn(),
  getSessionHistory: vi.fn(),
  getAssessmentQuestions: vi.fn(),
  submitAssessment: vi.fn(),
  getAssessmentHistory: vi.fn(),
}))

import * as api from '@/lib/api'
import { usePatientSessions } from '@/hooks/usePatientSessions'
import { useSessionMessages } from '@/hooks/useSessionMessages'
import { useAssessmentHistory } from '@/hooks/useAssessmentHistory'
import { PatientPortal } from '@/components/patient/PatientPortal'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const mockSession = {
  id: 'sess-001',
  patientId: 'pat-001',
  stage: 2 as const,
  currentStep: 3,
  status: 'completed' as const,
  crisisScore: 0.15,
  startedAt: '2026-03-07T10:30:00Z',
}

const mockAssessmentHistory = [
  {
    id: 'asr-001',
    patientId: 'pat-001',
    assessmentType: 'PHQ-9',
    score: 12,
    severity: 'Moderate',
    administeredAt: '2026-03-06T09:00:00Z',
  },
  {
    id: 'asr-002',
    patientId: 'pat-001',
    assessmentType: 'GAD-7',
    score: 8,
    severity: 'Mild',
    administeredAt: '2026-03-07T11:00:00Z',
  },
]

const mockMessages = [
  { id: 'msg-1', sessionId: 'sess-001', role: 'user' as const, content: 'Hello', createdAt: '2026-03-07T10:30:01Z' },
  { id: 'msg-2', sessionId: 'sess-001', role: 'assistant' as const, content: 'Hi there!', createdAt: '2026-03-07T10:30:05Z' },
]

// ─── Wrapper for hooks ────────────────────────────────────────────────────────

function HookWrapper({ hook }: { hook: () => unknown }) {
  const result = hook()
  ;(window as Record<string, unknown>).__hookResult__ = result
  return null
}

function getHookResult<T>() {
  return (window as Record<string, unknown>).__hookResult__ as T
}

// ─── usePatientSessions ───────────────────────────────────────────────────────

describe('usePatientSessions', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns loading=true initially then sessions on success', async () => {
    vi.mocked(api.listPatientSessions).mockResolvedValueOnce({
      data: { sessions: [mockSession] },
    } as never)

    render(<HookWrapper hook={() => usePatientSessions('pat-001')} />)

    await waitFor(() => {
      const result = getHookResult<ReturnType<typeof usePatientSessions>>()
      expect(result.loading).toBe(false)
      expect(result.sessions).toHaveLength(1)
      expect(result.sessions[0].id).toBe('sess-001')
    })
  })

  it('sets error state when API call fails', async () => {
    vi.mocked(api.listPatientSessions).mockRejectedValueOnce({
      response: { data: { detail: 'Patient not found' } },
    })

    render(<HookWrapper hook={() => usePatientSessions('bad-id')} />)

    await waitFor(() => {
      const result = getHookResult<ReturnType<typeof usePatientSessions>>()
      expect(result.loading).toBe(false)
      expect(result.error).toBe('Patient not found')
    })
  })

  it('does not fetch when patientId is anonymous', () => {
    render(<HookWrapper hook={() => usePatientSessions('anonymous')} />)
    expect(api.listPatientSessions).not.toHaveBeenCalled()
  })
})

// ─── useSessionMessages ───────────────────────────────────────────────────────

describe('useSessionMessages', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns messages on success', async () => {
    vi.mocked(api.getSessionHistory).mockResolvedValueOnce({
      data: { messages: mockMessages },
    } as never)

    render(<HookWrapper hook={() => useSessionMessages('sess-001')} />)

    await waitFor(() => {
      const result = getHookResult<ReturnType<typeof useSessionMessages>>()
      expect(result.loading).toBe(false)
      expect(result.messages).toHaveLength(2)
    })
  })

  it('does not fetch when sessionId is null', () => {
    render(<HookWrapper hook={() => useSessionMessages(null)} />)
    expect(api.getSessionHistory).not.toHaveBeenCalled()
  })

  it('sets error state on API failure', async () => {
    vi.mocked(api.getSessionHistory).mockRejectedValueOnce({
      response: { data: { detail: 'Session not found' } },
    })

    render(<HookWrapper hook={() => useSessionMessages('bad-sess')} />)

    await waitFor(() => {
      const result = getHookResult<ReturnType<typeof useSessionMessages>>()
      expect(result.error).toBe('Session not found')
    })
  })
})

// ─── useAssessmentHistory ──────────────────────────────────────────────────────

describe('useAssessmentHistory', () => {
  beforeEach(() => vi.clearAllMocks())

  it('returns loading=true initially then history on success', async () => {
    vi.mocked(api.getAssessmentHistory).mockResolvedValueOnce({
      data: { history: mockAssessmentHistory },
    } as never)

    render(<HookWrapper hook={() => useAssessmentHistory('pat-001')} />)

    await waitFor(() => {
      const result = getHookResult<ReturnType<typeof useAssessmentHistory>>()
      expect(result.loading).toBe(false)
      expect(result.history).toHaveLength(2)
      expect(result.history[0].assessmentType).toBe('PHQ-9')
    })
  })

  it('sets error state when API call fails', async () => {
    vi.mocked(api.getAssessmentHistory).mockRejectedValueOnce({
      response: { data: { detail: 'Patient not found' } },
    })

    render(<HookWrapper hook={() => useAssessmentHistory('bad-id')} />)

    await waitFor(() => {
      const result = getHookResult<ReturnType<typeof useAssessmentHistory>>()
      expect(result.loading).toBe(false)
      expect(result.error).toBe('Patient not found')
    })
  })

  it('does not fetch when patientId is anonymous', () => {
    render(<HookWrapper hook={() => useAssessmentHistory('anonymous')} />)
    expect(api.getAssessmentHistory).not.toHaveBeenCalled()
  })
})

// ─── PatientPortal — assessments tab ──────────────────────────────────────────

describe('PatientPortal assessment history', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('patient_id', 'pat-001')
    // sessions tab loads on mount — satisfy that mock too
    vi.mocked(api.listPatientSessions).mockResolvedValue({ data: { sessions: [] } } as never)
  })

  it('shows history cards with type, score, severity, and date', async () => {
    vi.mocked(api.getAssessmentHistory).mockResolvedValueOnce({
      data: { history: mockAssessmentHistory },
    } as never)

    render(<PatientPortal />)

    // switch to assessments tab
    fireEvent.click(screen.getByText('assessments'))

    await waitFor(() => {
      expect(screen.getByText('PHQ-9')).toBeTruthy()
      expect(screen.getByText('GAD-7')).toBeTruthy()
      expect(screen.getByText('Score: 12')).toBeTruthy()
      expect(screen.getByText('Score: 8')).toBeTruthy()
      expect(screen.getByText('Moderate')).toBeTruthy()
      expect(screen.getByText('Mild')).toBeTruthy()
    })
  })

  it('shows empty state when no history exists', async () => {
    vi.mocked(api.getAssessmentHistory).mockResolvedValueOnce({
      data: { history: [] },
    } as never)

    render(<PatientPortal />)
    fireEvent.click(screen.getByText('assessments'))

    await waitFor(() => {
      expect(screen.getByText('No past assessments')).toBeTruthy()
    })
  })

  it('shows loading skeletons while fetching history', () => {
    vi.mocked(api.getAssessmentHistory).mockReturnValueOnce(new Promise(() => {}))

    render(<PatientPortal />)
    fireEvent.click(screen.getByText('assessments'))

    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows error state with retry button on history API failure', async () => {
    vi.mocked(api.getAssessmentHistory).mockRejectedValueOnce({
      response: { data: { detail: 'History unavailable' } },
    })

    render(<PatientPortal />)
    fireEvent.click(screen.getByText('assessments'))

    await waitFor(() => {
      expect(screen.getByText('History unavailable')).toBeTruthy()
      expect(screen.getByText('Retry')).toBeTruthy()
    })
  })
})

// ─── PatientPortal — sessions tab ─────────────────────────────────────────────

describe('PatientPortal sessions tab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('patient_id', 'pat-001')
  })

  it('shows loading skeletons while fetching', () => {
    vi.mocked(api.listPatientSessions).mockReturnValueOnce(new Promise(() => {}))
    render(<PatientPortal />)
    // The animate-pulse skeletons should be visible
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders session cards with stage badge and crisis score', async () => {
    vi.mocked(api.listPatientSessions).mockResolvedValueOnce({
      data: { sessions: [mockSession] },
    } as never)

    render(<PatientPortal />)

    await waitFor(() => {
      expect(screen.getByText('Stage 2')).toBeTruthy()
      expect(screen.getByText(/Crisis: Low/)).toBeTruthy()
    })
  })

  it('shows empty state when no sessions exist', async () => {
    vi.mocked(api.listPatientSessions).mockResolvedValueOnce({
      data: { sessions: [] },
    } as never)

    render(<PatientPortal />)

    await waitFor(() => {
      expect(screen.getByText('No sessions yet')).toBeTruthy()
    })
  })

  it('expands session card on click and loads messages', async () => {
    vi.mocked(api.listPatientSessions).mockResolvedValueOnce({
      data: { sessions: [mockSession] },
    } as never)
    vi.mocked(api.getSessionHistory).mockResolvedValueOnce({
      data: { messages: mockMessages },
    } as never)

    render(<PatientPortal />)

    // Wait for session card to appear
    await waitFor(() => screen.getByText('Stage 2'))

    // Click the card to expand
    const cardButton = document.querySelector('button[aria-expanded]') as HTMLButtonElement
    fireEvent.click(cardButton)

    // Messages should load
    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeTruthy()
      expect(screen.getByText('Hi there!')).toBeTruthy()
    })
  })

  it('shows error state with retry button on API failure', async () => {
    vi.mocked(api.listPatientSessions).mockRejectedValueOnce({
      response: { data: { detail: 'Server error' } },
    })

    render(<PatientPortal />)

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeTruthy()
      expect(screen.getByText('Retry')).toBeTruthy()
    })
  })
})
