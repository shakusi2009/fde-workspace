import { api } from '@/api'

export type VehicleAgentDriver = {
  id: number
  name: string
  vin: string
  vehicle_model: string
  address: string
  registration_city: string
}

export type VehicleAgentModel = {
  id: number
  model_id: string
  created_at: string
  updated_at: string
}

export type VehicleAgentChatResponse = {
  session_id: string
  model_id: string
  answer: string
  reasoning_summary: string[]
  internet_used: boolean
  sources: string[]
}

export function getVehicleAgentDrivers(keyword = '') {
  const params = new URLSearchParams({ keyword })
  return api<VehicleAgentDriver[]>(
    `/vehicle-agent/drivers/options?${params}`,
  )
}

export function getVehicleAgentModels() {
  return api<VehicleAgentModel[]>('/vlm-models')
}

export function sendVehicleAgentMessage(
  sessionId: string,
  modelId: string,
  driver: VehicleAgentDriver,
  message: string,
) {
  return api<VehicleAgentChatResponse>('/vehicle-agent/chat', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      model_id: modelId,
      driver,
      message,
    }),
  })
}
