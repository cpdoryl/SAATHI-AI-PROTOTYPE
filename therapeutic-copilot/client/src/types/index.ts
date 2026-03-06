// SAATHI AI — Shared TypeScript types

export type PatientStage = 'lead' | 'active' | 'dropout' | 'archived'
export type SessionStatus = 'pending' | 'in_progress' | 'completed' | 'crisis_escalated'

export interface Patient {
  id: string
  fullName: string
  phone?: string
  email?: string
  stage: PatientStage
  language: string
  dropoutRiskScore: number
  lastActive: string
  clinicianId?: string
}

export interface TherapySession {
  id: string
  patientId: string
  stage: 1 | 2 | 3
  currentStep: number
  status: SessionStatus
  crisisScore: number
  startedAt: string
  endedAt?: string
}

export interface ChatMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  crisisKeywordsDetected?: string[]
}

export interface AssessmentResult {
  id: string
  patientId: string
  assessmentType: string
  score: number
  severity: string
  administeredAt: string
}

export interface Appointment {
  id: string
  patientId: string
  clinicianId: string
  scheduledAt: string
  durationMinutes: number
  status: 'scheduled' | 'confirmed' | 'completed' | 'cancelled'
  amountInr: number
  paymentStatus: string
}

export interface CrisisAlert {
  sessionId: string
  patientId: string
  severity: number
  detectedKeywords: string[]
  timestamp: string
}

export interface Tenant {
  id: string
  name: string
  domain: string
  plan: 'basic' | 'professional' | 'enterprise'
  isActive: boolean
}
