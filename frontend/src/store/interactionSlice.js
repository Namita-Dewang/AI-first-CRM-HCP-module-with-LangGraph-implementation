import { createSlice, nanoid } from '@reduxjs/toolkit'

// Maps the backend's snake_case state keys to the frontend's camelCase
// Redux fields, so hydrateFromAgent actually writes into the right slots.
const FIELD_MAP = {
  interaction_id: 'interactionId',
  hcp_id: 'hcpId',
  hcp_name: 'hcpName',
  interaction_type: 'interactionType',
  topics_discussed: 'topicsDiscussed',
  materials_shared: 'materialsShared',
  samples_distributed: 'samplesDistributed',
  follow_up_actions: 'followUpActions',
  compliance_flags: 'complianceFlags',
  ai_suggested_follow_ups: 'aiSuggestedFollowUps',
}

const initialState = {
  interactionId: null,
  hcpName: '',
  interactionType: '',
  date: '',
  time: '',
  attendees: '',
  topicsDiscussed: '',
  materialsShared: [],
  samplesDistributed: [],
  sentiment: '',
  outcomes: '',
  followUpActions: '',
  aiSuggestedFollowUps: [],
  chatMessages: [
    {
      id: 'seed-1',
      role: 'assistant',
      text:
        'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
    },
  ],
}

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    setField(state, action) {
      const { field, value } = action.payload
      state[field] = value
    },
    addMaterial(state, action) {
      state.materialsShared.push(action.payload)
    },
    addSample(state, action) {
      state.samplesDistributed.push(action.payload)
    },
    setSentiment(state, action) {
      state.sentiment = action.payload
    },
    sendChatMessage(state, action) {
      state.chatMessages.push({ id: nanoid(), role: 'user', text: action.payload })
    },
    receiveAssistantMessage(state, action) {
      state.chatMessages.push({ id: nanoid(), role: 'assistant', text: action.payload })
    },
    // Called with the `form_state` payload returned from the FastAPI /chat
    // endpoint so a chat turn can hydrate the structured form fields.
    hydrateFromAgent(state, action) {
      Object.entries(action.payload || {}).forEach(([key, value]) => {
        const mappedKey = FIELD_MAP[key] || key
        if (mappedKey in state) state[mappedKey] = value
      })
    },
    removeFollowUpSuggestion(state, action) {
      state.aiSuggestedFollowUps = state.aiSuggestedFollowUps.filter(
        (_, i) => i !== action.payload
      )
    },
  },
})

export const {
  setField,
  addMaterial,
  addSample,
  setSentiment,
  sendChatMessage,
  receiveAssistantMessage,
  hydrateFromAgent,
  removeFollowUpSuggestion,
} = interactionSlice.actions

export default interactionSlice.reducer