/**
 * SAATHI AI — API Client
 * Axios-based HTTP client with JWT auth header injection.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Inject JWT token from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('saathi_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 → redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('saathi_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password })

export const register = (data: object) =>
  api.post('/auth/register', data)

// ─── Chat ─────────────────────────────────────────────────────────────────────

export const startSession = (data: object) =>
  api.post('/chat/start', data)

export const sendMessage = (sessionId: string, message: string, stage: number) =>
  api.post('/chat/message', { session_id: sessionId, message, stage })

export const getSessionHistory = (sessionId: string) =>
  api.get(`/chat/session/${sessionId}`)

// ─── Assessments ──────────────────────────────────────────────────────────────

export const getAssessmentQuestions = (type: string) =>
  api.get(`/assessments/${type}/questions`)

export const submitAssessment = (patientId: string, data: object) =>
  api.post(`/assessments/${patientId}/submit`, data)

export const getAssessmentHistory = (patientId: string) =>
  api.get(`/assessments/${patientId}/history`)

// ─── Appointments ─────────────────────────────────────────────────────────────

export const createAppointment = (data: object) =>
  api.post('/appointments', data)

export const listAppointments = () =>
  api.get('/appointments')

export const cancelAppointment = (id: string) =>
  api.put(`/appointments/${id}/cancel`)

// ─── Payments ────────────────────────────────────────────────────────────────

export const createPaymentOrder = (data: object) =>
  api.post('/payments/create-order', data)

export const verifyPayment = (data: object) =>
  api.post('/payments/verify', data)

// ─── Patients ────────────────────────────────────────────────────────────────

export const listPatients = () =>
  api.get('/patients')

export const getPatient = (patientId: string) =>
  api.get(`/patients/${patientId}`)

export const listPatientSessions = (patientId: string) =>
  api.get(`/patients/${patientId}/sessions`)

// ─── Leads ───────────────────────────────────────────────────────────────────

export const listLeads = () =>
  api.get('/leads')

export const convertLead = (leadId: string) =>
  api.put(`/leads/${leadId}/convert`)

export default api
