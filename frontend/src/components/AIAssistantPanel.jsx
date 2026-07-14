import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Bot, Zap } from 'lucide-react'
import { sendChatMessage, receiveAssistantMessage, hydrateFromAgent } from '../store/interactionSlice'
import '../styles/AIAssistantPanel.css'

// Points at the FastAPI backend's chat endpoint (see backend/app/routers/chat.py).
// During local dev this is usually http://localhost:8000.
const CHAT_ENDPOINT = 'http://localhost:8000/api/interactions/chat'
const THREAD_ID = 'demo-session'

export default function AIAssistantPanel() {
  const dispatch = useDispatch()
  const messages = useSelector((s) => s.interaction.chatMessages)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  const handleLog = async () => {
  const text = draft.trim()
  if (!text) return
  dispatch(sendChatMessage(text))
  setDraft('')
  setSending(true)
  try {
    const res = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, thread_id: THREAD_ID }),
    })
    const data = await res.json()

    if (!res.ok) {
      const detail = data.detail || `Server error (${res.status})`
      dispatch(receiveAssistantMessage(`Something went wrong: ${detail}`))
      return
    }

    dispatch(receiveAssistantMessage(data.reply))
    if (data.form_state) dispatch(hydrateFromAgent(data.form_state))
  } catch (err) {
    dispatch(
      receiveAssistantMessage(
        "I couldn't reach the backend agent. Make sure the FastAPI server is running on port 8000."
      )
    )
  } finally {
    setSending(false)
  }
}
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleLog()
    }
  }

  return (
    <section className="panel assistant-panel">
      <div className="assistant-header">
        <span className="assistant-icon">
          <Bot size={16} />
        </span>
        <div>
          <div className="assistant-title">AI Assistant</div>
          <div className="assistant-subtitle">Log interaction via chat</div>
        </div>
      </div>

      <div className="assistant-messages">
        {messages.map((m) => (
          <div key={m.id} className={`chat-bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

      <div className="assistant-input-row">
        <input
          className="assistant-input"
          placeholder="Describe interaction..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="log-button" type="button" onClick={handleLog} disabled={sending}>
          <Zap size={14} />
          Log
        </button>
      </div>
    </section>
  )
}
