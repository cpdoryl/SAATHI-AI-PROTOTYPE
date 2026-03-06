/**
 * SAATHI AI — Embeddable Widget Entry Point
 *
 * Deployment:
 *   <script src="https://api.saathi-ai.com/api/v1/widget/bundle.js"
 *           data-token="YOUR_WIDGET_TOKEN"></script>
 *
 * Architecture:
 *   - Uses Shadow DOM for complete CSS isolation (no style conflicts)
 *   - Self-contained React app mounted inside the Shadow DOM
 *   - Communicates with Saathi AI backend via REST + WebSocket
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChatBubble } from './components/ChatBubble'

class SaathiWidget extends HTMLElement {
  private shadowRoot!: ShadowRoot

  connectedCallback() {
    // Create Shadow DOM for complete isolation
    this.shadowRoot = this.attachShadow({ mode: 'closed' })

    // Inject Tailwind CSS reset inside shadow root
    const style = document.createElement('style')
    style.textContent = `
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      :host { position: fixed; bottom: 24px; right: 24px; z-index: 999999; font-family: 'Inter', system-ui, sans-serif; }
    `
    this.shadowRoot.appendChild(style)

    // React mount point
    const container = document.createElement('div')
    this.shadowRoot.appendChild(container)

    // Get widget token from script tag data attribute
    const script = document.currentScript as HTMLScriptElement
    const token = script?.dataset?.token || this.getAttribute('data-token') || ''

    // Mount React widget inside Shadow DOM
    ReactDOM.createRoot(container).render(
      React.createElement(ChatBubble, { widgetToken: token })
    )
  }
}

// Register custom element — avoid re-registering if already defined
if (!customElements.get('saathi-widget')) {
  customElements.define('saathi-widget', SaathiWidget)
}

// Auto-inject the custom element into the page
const el = document.createElement('saathi-widget')
document.body.appendChild(el)
