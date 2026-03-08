# SAATHI AI — Widget Blueprint
## Shadow DOM + Custom Elements + React 18
### Version: 1.0 | Date: 2026-03-08 | Status: In Progress

---

## PURPOSE
The SAATHI AI widget is an embeddable chat bubble that any clinic can add to
their website with one `<script>` tag. It is fully isolated via Shadow DOM
so it never conflicts with the host site's CSS or JS.

---

## 1. EMBED CODE (what clinic gets)

```html
<!-- Paste this anywhere on your website -->
<script
  src="https://cdn.saathai.in/widget/saathi-widget.js"
  data-token="YOUR_CLINIC_WIDGET_TOKEN"
  async
></script>
```

---

## 2. CURRENT STATUS

| Feature | File | Status |
|---------|------|--------|
| Custom Element registration | `widget.ts` | ✓ DONE |
| Shadow DOM `mode: 'closed'` | `widget.ts` | ✓ DONE |
| `data-token` extraction | `widget.ts` | ✓ DONE |
| React 18 mount in shadow root | `widget.ts` | ✓ DONE |
| Auto-inject `<saathi-widget>` on load | `widget.ts` | ✓ DONE |
| CSS reset inside shadow DOM | `widget.ts` | ✓ DONE |
| Chat bubble UI | `ChatBubble.tsx` | PARTIAL |
| Token validation API call | — | MISSING |
| WebSocket chat connection | — | MISSING |
| Token streaming display | — | MISSING |
| Crisis banner inside widget | — | MISSING |
| Offline/error state | — | MISSING |
| Mobile responsive | — | MISSING |

---

## 3. ChatBubble COMPONENT REQUIREMENTS

### Visual Design
- Floating button: bottom-right corner, 60px circle, SAATHI logo/icon
- Click → expand to chat panel (320px wide × 480px tall)
- Chat panel has: header (clinic logo + "Chat with Saathi"), message area, input bar
- Color theme: indigo primary (#6366f1), white background
- Mobile: full-screen on screens < 480px width

### Functional Requirements
```
1. On mount:
   - Call GET /api/v1/widget/validate-token?token={data-token}
   - If invalid → hide widget silently (no errors shown to patient)
   - If valid → show chat bubble

2. On bubble click (first time):
   - Call POST /api/v1/chat/session with {patient_id: "anonymous", widget_token}
   - Receive {session_id, stage, greeting}
   - Open WebSocket: ws://api/ws/chat/{session_id}
   - Display greeting message

3. On message send:
   - Send via WebSocket: {type: "message", content: userText}
   - Show user bubble immediately
   - Show typing indicator (animated dots)
   - Receive token stream → append to assistant bubble in real time
   - On {type: "done"} → stop typing indicator

4. On crisis detection:
   - Receive {type: "crisis", resources: [...]}
   - Show red banner: "Are you in distress? Here are some resources:"
   - List helplines (iCall, Vandrevala, NIMHANS)
   - Keep chat open

5. On panel close:
   - Session persists (WebSocket stays open in background)
   - Re-open → shows message history

6. On page unload:
   - Call POST /api/v1/chat/session/{id}/end
   - Close WebSocket cleanly
```

---

## 4. PENDING WIDGET TASKS

| Task | Priority |
|------|----------|
| Implement token validation in widget.ts on mount | CRITICAL |
| Full ChatBubble UI: bubble button + expandable panel | CRITICAL |
| WebSocket connection + token streaming | CRITICAL |
| Typing indicator (animated 3 dots) | HIGH |
| Crisis banner component | HIGH |
| Message history persistence (sessionStorage) | HIGH |
| Mobile responsive (full-screen < 480px) | HIGH |
| Offline state handling | MEDIUM |
| Widget E2E test (Playwright) | MEDIUM |
| Vite build output as single JS file | HIGH |

---

## 5. BUILD OUTPUT

Vite builds to single file: `widget/dist/saathi-widget.js`
- All React, CSS, and logic bundled
- No external dependencies loaded at runtime
- Shadow DOM prevents any style leakage

---

## 6. COMPLETION CRITERIA

Widget is complete when:
- [ ] Embed code added to a blank HTML page → bubble appears
- [ ] Invalid token → widget hidden, no console errors
- [ ] Valid token → bubble shown, click → chat panel opens with greeting
- [ ] Message sent → response streams token by token
- [ ] Crisis keyword → red banner with helplines appears
- [ ] Widget works on mobile (320px viewport)
- [ ] `vite build` produces single `saathi-widget.js` under 500KB
