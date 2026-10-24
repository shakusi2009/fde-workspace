import { api } from '@/api'

export type Driver = {
  id: number
  name: string
  phone: string
  vin: string
  vehicle_model: string
  address: string
  registration_city: string
  registration_date: string
  create_time: string
  update_time: string
}

export type DriverPage = {
  items: Driver[]
  total: number
  page: number
  page_size: number
}

export type DriverOption = {
  id: number
  name: string
  vin: string
  vehicle_model: string
  registration_city: string
}

export type DriverPayload = {
  name: string
  phone: string
  vin: string
  vehicle_model: string
  address: string
  registration_city: string
  registration_date: string
}

export function getDrivers(page = 1, keyword = '') {
  const params = new URLSearchParams({
    page: String(page),
    keyword,
  })
  return api<DriverPage>(`/agent-data/drivers?${params}`)
}

export function getDriverOptions(keyword = '') {
  const params = new URLSearchParams({ keyword })
  return api<DriverOption[]>(`/agent-data/drivers/options?${params}`)
}

export function createDriver(payload: DriverPayload) {
  return api<{ id: number; message: string }>('/agent-data/drivers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateDriver(driverId: number, payload: DriverPayload) {
  return api<{ message: string }>(`/agent-data/drivers/${driverId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteDriver(driverId: number) {
  return api<{ message: string }>(`/agent-data/drivers/${driverId}`, {
    method: 'DELETE',
  })
}
