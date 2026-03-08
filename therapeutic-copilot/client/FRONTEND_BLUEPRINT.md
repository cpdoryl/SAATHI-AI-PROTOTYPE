# SAATHI AI — Frontend Blueprint
## React 18 + TypeScript + Vite + Tailwind CSS
### Version: 1.0 | Date: 2026-03-08 | Status: In Progress

---

## PURPOSE
This blueprint defines every frontend page, component, UI/UX requirement, API
wiring, routing, and test target. The autonomous AI agent reads this before any
frontend task.

---

## 1. TECH STACK

| Component | Choice | Version |
|-----------|--------|---------|
| Framework | React | 18 |
| Language | TypeScript | 5.x |
| Build tool | Vite | 5.x |
| Styling | Tailwind CSS | 3.x |
| Routing | React Router | 6 |
| State | Zustand + React Context | latest |
| Server state | TanStack Query (React Query) | 5 |
| HTTP client | Axios | latest |
| Charts | Recharts | latest |
| Real-time | WebSocket (native) + SSE | native |
| Testing | Vitest + React Testing Library | latest |

---

## 2. APPLICATION PAGES & ROUTES

```
/                           → LandingPage
/login                      → LoginPage (clinician auth)
/register                   → RegisterPage
/dashboard                  → ClinicianDashboard [Protected]
/dashboard/patients         → Patient list tab
/dashboard/sessions         → Session history tab
/dashboard/analytics        → Analytics tab
/dashboard/appointments     → Appointment calendar tab
/patient                    → PatientPortal [Protected - patient role]
/patient/assessments        → Assessment flow
/patient/sessions           → Session history
/patient/appointments       → Appointment booking
/admin                      → AdminPanel [Protected - admin role]
/admin/tenants              → Tenant management
/admin/rag-ingest           → Document upload for RAG
/payment/:appointmentId     → PaymentFlow
```

---

## 3. COMPONENT MAP & STATUS

### LandingPage (`components/landing/LandingPage.tsx`)
**Purpose**: Marketing page. Converts clinic visitors to signups.

| Section | Content | Status |
|---------|---------|--------|
| Hero | Headline + CTA button "Get Started" | ✓ EXISTS |
| Features | 3-column grid of benefits | ✓ EXISTS |
| How It Works | 3-step diagram | MISSING |
| Pricing | 3-tier card (Basic/Pro/Enterprise) | MISSING |
| Footer | Links, copyright | MISSING |

**Pending**:
- [ ] Add How It Works section with animated steps
- [ ] Add Pricing cards (Basic ₹2,999/mo, Pro ₹7,999/mo, Enterprise custom)
- [ ] Add Footer with nav links
- [ ] Make all CTAs link to `/register`

---

### LoginPage + RegisterPage
**Purpose**: Clinician authentication.

| Feature | Status |
|---------|--------|
| Email + password form | ✓ EXISTS |
| bcrypt error handling ("Invalid credentials") | ✓ EXISTS |
| JWT stored in localStorage | ✓ EXISTS |
| Redirect to /dashboard on success | ✓ EXISTS |
| Show/hide password toggle | MISSING |
| "Forgot password?" link | MISSING |
| Form validation (email format, min 8 chars) | MISSING |

**Pending**:
- [ ] Add inline validation (red border + error text on blur)
- [ ] Add show/hide password toggle
- [ ] Add loading spinner on submit button

---

### ClinicianDashboard (`components/clinician/ClinicianDashboard.tsx`)
**Purpose**: Clinician's main workspace. 4 tabs.

#### Tab 1 — Patients
| Feature | Status |
|---------|--------|
| Patient list from `GET /api/v1/patients` | ✓ DONE |
| Patient name + stage badge (LEAD/ACTIVE/DROPOUT) | ✓ EXISTS |
| Dropout risk score colored badge (red/yellow/green) | MISSING |
| Click patient → opens patient detail drawer | MISSING |
| Session count per patient | MISSING |
| Search/filter patients by name or stage | MISSING |

#### Tab 2 — Crisis Alerts
| Feature | Status |
|---------|--------|
| Real-time WebSocket connection to clinician room | ✓ EXISTS |
| Incoming crisis alert card (patient, severity, timestamp) | ✓ EXISTS |
| Alert dismissal | MISSING |
| Click alert → opens session detail | MISSING |

#### Tab 3 — Analytics
| Feature | Status |
|---------|--------|
| Total active patients count | MISSING |
| Sessions this week bar chart | MISSING |
| Crisis detection rate line chart | MISSING |
| Assessment score distributions | MISSING |
| Dropout risk heatmap | MISSING |

**Implementation**:
- Fetch data from `GET /api/v1/leads`, `GET /api/v1/patients`, session counts
- Use Recharts: `BarChart`, `LineChart`, `PieChart`

#### Tab 4 — Appointments
| Feature | Status |
|---------|--------|
| Appointment list from `GET /api/v1/appointments` | MISSING |
| Calendar view (weekly) | MISSING |
| Create appointment button | MISSING |
| Cancel appointment with refund | MISSING |

**Pending for Dashboard**:
- [ ] Patient risk score badge (red >0.7, yellow 0.3-0.7, green <0.3)
- [ ] Patient detail slide-over drawer with session history
- [ ] Analytics tab: 4 Recharts components wired to real API data
- [ ] Appointments tab: list + create form + cancel
- [ ] Search/filter bar on patients tab

---

### PatientPortal (`components/patient/PatientPortal.tsx`)
**Purpose**: Patient's self-service portal. 3 tabs.

#### Tab 1 — Assessments
| Feature | Status |
|---------|--------|
| Assessment type selector (8 types) | ✓ DONE |
| Question form with Likert scale | ✓ DONE |
| Score + severity display on submit | ✓ DONE |
| Assessment history from `GET /api/v1/assessments/{id}/history` | STUB — placeholder text |

#### Tab 2 — Session History
| Feature | Status |
|---------|--------|
| List sessions from `GET /api/v1/patients/{id}/sessions` | STUB — placeholder text |
| Session card: date, stage, summary, crisis_score | MISSING |
| Click session → expand messages | MISSING |

#### Tab 3 — Appointments
| Feature | Status |
|---------|--------|
| List appointments from `GET /api/v1/appointments` | STUB — placeholder text |
| Book new appointment: clinician selector + date picker | MISSING |
| Payment flow trigger on booking | MISSING |
| Cancel appointment | MISSING |

**Pending for PatientPortal**:
- [ ] Assessment history: query `GET /api/v1/assessments/{id}/history` + render history cards
- [ ] Session history: query real API + render session cards with expandable messages
- [ ] Appointments: list + book (date picker + clinician selector + PaymentFlow trigger)

---

### ChatWidget (`components/chatbot/ChatWidget.tsx`)
**Purpose**: The core therapeutic chat interface embedded in PatientPortal.

| Feature | Status |
|---------|--------|
| WebSocket connection to `/ws/chat/{session_id}` | UNKNOWN |
| Send message input + button | UNKNOWN |
| Message history display (user/assistant bubbles) | UNKNOWN |
| Real-time token streaming display | UNKNOWN |
| Crisis alert banner when detected | MISSING |
| Typing indicator during LLM generation | MISSING |
| Session end button + summary display | MISSING |
| Auto-scroll to latest message | MISSING |

**This is the most critical UI component for the investor demo.**

**Implementation requirements**:
```typescript
// WebSocket connection
const ws = new WebSocket(`ws://api/ws/chat/${sessionId}`)
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'token') appendToken(data.token)
  if (data.type === 'crisis') showCrisisBanner(data.resources)
}
```

**Pending**:
- [ ] Full ChatWidget implementation: WS connect, send, stream tokens, display messages
- [ ] Crisis banner component (red overlay with helpline numbers)
- [ ] Typing indicator (animated dots during AI generation)
- [ ] Session end + AI summary modal
- [ ] Auto-scroll hook

---

### PaymentFlow (`components/payment/PaymentFlow.tsx`)
**Purpose**: Razorpay checkout for appointment booking.

| Feature | Status |
|---------|--------|
| Create order from `POST /api/v1/payments/create-order` | ✓ EXISTS |
| Load Razorpay SDK dynamically | ✓ EXISTS |
| Razorpay modal with prefill | ✓ EXISTS |
| Verify payment via backend | ✓ EXISTS |
| Success/failure callbacks | ✓ EXISTS |
| Razorpay SDK script in `index.html` | MISSING |

**Pending**:
- [ ] Add `<script src="https://checkout.razorpay.com/v1/checkout.js">` to `client/index.html`
- [ ] Test full flow in Razorpay sandbox mode
- [ ] Add loading state during payment processing

---

### AdminPanel (`components/admin/AdminPanel.tsx`)
**Purpose**: Platform admin — tenant management, RAG ingestion.

| Feature | Status |
|---------|--------|
| Tenant list from `GET /api/v1/tenants` | UNKNOWN |
| Create tenant form | UNKNOWN |
| RAG document upload UI | MISSING |
| Widget token display per tenant | MISSING |

**Pending**:
- [ ] Tenant CRUD table
- [ ] Document upload form → `POST /api/v1/rag/ingest` with file + tenant_id
- [ ] Widget embed code generator (shows `<script>` tag with widget_token)

---

### Analytics (`components/analytics/Analytics.tsx`)
**Purpose**: Charts for platform-level metrics.

**Charts needed** (all using Recharts):
- [ ] Daily active sessions: LineChart
- [ ] Crisis detection rate: AreaChart
- [ ] Assessment score distribution: BarChart (per type)
- [ ] Patient stage funnel: PieChart (LEAD → ACTIVE → DROPOUT)
- [ ] Appointment completion rate: RadialBar

---

## 4. API CLIENT (`lib/api.ts`) — COMPLETE SPEC

Current status: ✓ COMPLETE for all existing endpoints.

**Missing API functions to add**:
```typescript
// Session history for patient portal
export const getPatientSessions = (patientId: string) =>
  api.get(`/patients/${patientId}/sessions`)

// Assessment history
export const getAssessmentHistory = (patientId: string) =>
  api.get(`/assessments/${patientId}/history`)

// Appointments
export const getAppointments = () => api.get('/appointments')
export const createAppointment = (data: AppointmentPayload) =>
  api.post('/appointments', data)
export const cancelAppointment = (id: string) =>
  api.put(`/appointments/${id}/cancel`)

// Analytics
export const getAnalyticsSummary = () => api.get('/analytics/summary')

// Admin - RAG ingestion
export const ingestDocument = (tenantId: string, content: string, metadata: object) =>
  api.post('/rag/ingest', { tenant_id: tenantId, content, metadata })

// Auth
export const getCurrentUser = () => api.get('/auth/me')
export const logout = () => api.post('/auth/logout')
```

---

## 5. REAL-TIME REQUIREMENTS

### WebSocket Connections

| Connection | Path | Data format | Purpose |
|-----------|------|-------------|---------|
| Chat stream | `/ws/chat/{session_id}` | `{type: "token"|"crisis"|"done", ...}` | Token streaming |
| Clinician alerts | `/ws/clinician/{clinician_id}` | `{type: "crisis_alert", patient, severity, resources}` | Real-time alerts |

### useChat Hook (`hooks/useChat.ts`)
Must provide:
```typescript
const {
  messages,        // ChatMessage[]
  sendMessage,     // (text: string) => void
  isStreaming,     // boolean
  crisisDetected,  // boolean
  crisisResources, // string[]
  endSession,      // () => Promise<Summary>
} = useChat(sessionId)
```

---

## 6. TYPESCRIPT TYPES REQUIRED (`types/index.ts`)

```typescript
interface Patient { id, full_name, stage, dropout_risk_score, last_active, tenant_id }
interface TherapySession { id, patient_id, stage, current_step, status, crisis_score, started_at }
interface ChatMessage { id, session_id, role, content, created_at }
interface Assessment { id, patient_id, assessment_type, score, severity, administered_at }
interface Appointment { id, patient_id, clinician_id, scheduled_at, status, amount_inr, payment_status }
interface CrisisAlert { session_id, patient_id, severity, keywords, resources }
interface Tenant { id, name, domain, widget_token, plan }
```

---

## 7. TESTING REQUIREMENTS

All tests in `client/src/__tests__/`:

| Test File | What to Test |
|-----------|-------------|
| `auth.test.tsx` | Login form submit → API call, JWT stored, redirect |
| `clinician-dashboard.test.tsx` | Patient list renders from API mock, tab switching |
| `patient-portal.test.tsx` | Assessment form → submit → score displayed |
| `chat-widget.test.tsx` | WebSocket mock → token stream → message displayed |
| `payment-flow.test.tsx` | Create order → Razorpay mock → verify called |

**Setup**: Vitest + React Testing Library + MSW (Mock Service Worker) for API mocking

---

## 8. UX STANDARDS

- All forms show inline validation errors (red border + helper text)
- All async actions show loading state (spinner or skeleton)
- All errors show toast notification (top-right, auto-dismiss 4s)
- Mobile-first responsive: breakpoints sm/md/lg (Tailwind)
- Color palette: primary `#6366f1` (indigo), crisis `#ef4444` (red), success `#22c55e` (green)
- Font: Inter (Google Fonts)
- All clickable elements have `hover:` and `focus:` states
- Empty states show illustrated placeholder, not blank space

---

## 9. COMPLETION CRITERIA

Frontend is prototype-complete when:
- [ ] All pages render without console errors
- [ ] All API calls use real backend (no mocked/hardcoded data)
- [ ] Chat widget streams tokens in real time
- [ ] Crisis alert appears in clinician dashboard within 2 seconds of detection
- [ ] Assessment flow: select type → answer → see score
- [ ] Payment flow: book appointment → Razorpay modal → confirmation
- [ ] Vitest tests pass: `npm run test`
- [ ] Build succeeds: `npm run build` (no TypeScript errors)
