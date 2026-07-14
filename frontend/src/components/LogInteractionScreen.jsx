import InteractionForm from './InteractionForm'
import AIAssistantPanel from './AIAssistantPanel'
import '../styles/LogInteractionScreen.css'

export default function LogInteractionScreen() {
  return (
    <div className="screen">
      <h1 className="screen-title">Log HCP Interaction</h1>
      <div className="screen-grid">
        <InteractionForm />
        <AIAssistantPanel />
      </div>
    </div>
  )
}
