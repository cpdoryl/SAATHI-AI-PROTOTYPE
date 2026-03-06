/**
 * SAATHI AI — Embeddable Chat Bubble Component
 * Floating action button + expandable chat panel (Tidio-style)
 * Runs inside Shadow DOM — fully isolated from host page styles.
 */
import React, { useState, useRef, useEffect } from 'react'

interface ChatBubbleProps {
  widgetToken: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function ChatBubble({ widgetToken }: ChatBubbleProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [config, setConfig] = useState({ persona_name: 'Saathi', primary_color: '#4F46E5', greeting: '' })
  const endRef = useRef<HTMLDivElement>(null)

  // Fetch widget config from Saathi AI backend
  useEffect(() => {
    if (!widgetToken) return
    fetch('/api/v1/widget/config', {
      headers: { 'X-Widget-Token': widgetToken },
    })
      .then((r) => r.json())
      .then((data) => {
        setConfig(data)
        if (data.greeting) {
          setMessages([{ id: '0', role: 'assistant', content: data.greeting }])
        }
      })
      .catch(console.error)
  }, [widgetToken])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const sendMessage = async () => {
    if (!input.trim()) return
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsTyping(true)

    try {
      const res = await fetch('/api/v1/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Widget-Token': widgetToken },
        body: JSON.stringify({ session_id: sessionId, message: input, stage: 1 }),
      })
      const data = await res.json()
      setMessages((prev) => [...prev, { id: Date.now().toString() + '_ai', role: 'assistant', content: data.response }])
      if (data.session_id) setSessionId(data.session_id)
    } catch (err) {
      setMessages((prev) => [...prev, { id: 'err', role: 'assistant', content: "I'm having trouble connecting. Please try again." }])
    } finally {
      setIsTyping(false)
    }
  }

  const color = config.primary_color

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* Chat Panel */}
      {isOpen && (
        <div style={{
          position: 'fixed', bottom: '80px', right: '16px',
          width: '360px', height: '520px',
          backgroundColor: '#fff', borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{ backgroundColor: color, padding: '16px', color: '#fff' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: '16px' }}>{config.persona_name}</div>
                <div style={{ fontSize: '12px', opacity: 0.8 }}>Therapeutic Co-Pilot</div>
              </div>
              <button onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '20px' }}>✕</button>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {messages.map((msg) => (
              <div key={msg.id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '75%', padding: '10px 14px', borderRadius: '16px', fontSize: '14px', lineHeight: 1.5,
                  backgroundColor: msg.role === 'user' ? color : '#f3f4f6',
                  color: msg.role === 'user' ? '#fff' : '#1f2937',
                }}>
                  {msg.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div style={{ display: 'flex', gap: '4px', padding: '10px 14px', backgroundColor: '#f3f4f6', borderRadius: '16px', width: 'fit-content' }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#9ca3af', animation: `bounce 1s infinite ${i * 0.15}s` }} />
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div style={{ padding: '12px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '8px' }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..."
              style={{
                flex: 1, padding: '10px 14px', borderRadius: '24px', border: '1px solid #e5e7eb',
                fontSize: '14px', outline: 'none',
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim()}
              style={{
                width: '40px', height: '40px', borderRadius: '50%', backgroundColor: color,
                border: 'none', cursor: 'pointer', color: '#fff', fontSize: '16px',
                opacity: input.trim() ? 1 : 0.5,
              }}
            >
              ↑
            </button>
          </div>
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed', bottom: '16px', right: '16px',
          width: '56px', height: '56px', borderRadius: '50%',
          backgroundColor: color, border: 'none', cursor: 'pointer',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '24px', color: '#fff',
          transition: 'transform 0.2s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
      >
        {isOpen ? '✕' : '💬'}
      </button>
    </div>
  )
}
