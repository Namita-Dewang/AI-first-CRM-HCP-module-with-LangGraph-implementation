import { useDispatch, useSelector } from 'react-redux'
import { Search, ChevronDown, Calendar, Clock, Mic, Zap, PackagePlus, Smile, Meh, Frown } from 'lucide-react'
import { setField, addMaterial, addSample, setSentiment } from '../store/interactionSlice'
import '../styles/InteractionForm.css'

const SENTIMENTS = [
  { key: 'Positive', Icon: Smile, color: '#4f9d5c' },
  { key: 'Neutral', Icon: Meh, color: '#e08a1e' },
  { key: 'Negative', Icon: Frown, color: '#d1553f' },
]

export default function InteractionForm() {
  const dispatch = useDispatch()
  const state = useSelector((s) => s.interaction)

  const update = (field) => (e) => dispatch(setField({ field, value: e.target.value }))

  return (
    <section className="panel form-panel">
      <h2 className="panel-title">Interaction Details</h2>

      <div className="field-row">
        <div className="field">
          <label className="field-label">HCP Name</label>
          <input
            className="field-input"
            placeholder="Search or select HCP..."
            value={state.hcpName}
            onChange={update('hcpName')}
          />
        </div>
        <div className="field">
          <label className="field-label">Interaction Type</label>
          <div className="select-wrap">
            <select className="field-input select" value={state.interactionType} onChange={update('interactionType')}>
              <option>Meeting</option>
              <option>Call</option>
              <option>Email</option>
              <option>Conference</option>
            </select>
            <ChevronDown size={16} className="select-chevron" />
          </div>
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label className="field-label">Date</label>
          <div className="icon-input-wrap">
            <input className="field-input" value={state.date} onChange={update('date')} />
            <Calendar size={16} className="input-icon" />
          </div>
        </div>
        <div className="field">
          <label className="field-label">Time</label>
          <div className="icon-input-wrap">
            <input className="field-input" value={state.time} onChange={update('time')} />
            <Clock size={16} className="input-icon" />
          </div>
        </div>
      </div>

      <div className="field">
        <label className="field-label">Attendees</label>
        <input
          className="field-input"
          placeholder="Enter names or search..."
          value={state.attendees}
          onChange={update('attendees')}
        />
      </div>

      <div className="field">
        <label className="field-label">Topics Discussed</label>
        <div className="textarea-wrap">
          <textarea
            className="field-input"
            rows={3}
            placeholder="Enter key discussion points..."
            value={state.topicsDiscussed}
            onChange={update('topicsDiscussed')}
          />
          <Mic size={16} className="textarea-icon" />
        </div>
      </div>

      <button className="pill-button" type="button">
        <Zap size={14} />
        Summarize from Voice Note (Requires Consent)
      </button>

      <h3 className="section-subtitle">Materials Shared / Samples Distributed</h3>

      <div className="resource-row">
        <div>
          <div className="resource-label">Materials Shared</div>
          <div className="resource-empty">
            {state.materialsShared.length === 0
              ? 'No materials added.'
              : (Array.isArray(state.materialsShared) ? state.materialsShared.join(', ') : String(state.materialsShared))}
          </div>
        </div>
        <button
          className="outline-button"
          type="button"
          onClick={() => dispatch(addMaterial(`Material ${state.materialsShared.length + 1}`))}
        >
          <Search size={14} />
          Search/Add
        </button>
      </div>

      <div className="resource-row">
        <div>
          <div className="resource-label">Samples Distributed</div>
          <div className="resource-empty">
            {state.samplesDistributed.length === 0
              ? 'No samples added'
               : (Array.isArray(state.samplesDistributed) ? state.samplesDistributed.join(', ') : String(state.samplesDistributed))}
          </div>
        </div>
        <button
          className="outline-button"
          type="button"
          onClick={() => dispatch(addSample(`Sample ${state.samplesDistributed.length + 1}`))}
        >
          <PackagePlus size={14} />
          Add Sample
        </button>
      </div>

      <div className="field">
        <label className="field-label">Observed/Inferred HCP Sentiment</label>
        <div className="sentiment-row">
          {SENTIMENTS.map(({ key, Icon, color }) => {
            const active = state.sentiment === key
            return (
              <label key={key} className="sentiment-option">
                <Icon size={20} color={active ? color : '#c4c4cc'} />
                <span className="sentiment-radio-row">
                  <input
                    type="radio"
                    name="sentiment"
                    checked={active}
                    onChange={() => dispatch(setSentiment(key))}
                  />
                  <span className={active ? 'sentiment-label active' : 'sentiment-label'}>{key}</span>
                </span>
              </label>
            )
          })}
        </div>
      </div>

      <div className="field">
        <label className="field-label">Outcomes</label>
        <textarea
          className="field-input"
          rows={3}
          placeholder="Key outcomes or agreements..."
          value={state.outcomes}
          onChange={update('outcomes')}
        />
      </div>

      <div className="field">
        <label className="field-label">Follow-up Actions</label>
        <textarea
          className="field-input"
          rows={2}
          placeholder="Enter next steps or tasks..."
          value={state.followUpActions}
          onChange={update('followUpActions')}
        />
      </div>

      <div className="ai-followups">
        <div className="ai-followups-title">AI Suggested Follow-ups:</div>
        <ul>
          {state.aiSuggestedFollowUps.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  )
}
