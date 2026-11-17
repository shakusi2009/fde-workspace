import { api } from '@/api'

export type SalesPeriod = {
  year: number
  month: number
  period: string
  label: string
}

export type VehicleSalesRankItem = {
  rank: number
  series_id: number
  series_name: string
  brand_name: string
  manufacturer: string
  sales: number
  previous_rank: number | null
  image: string
  price: string
}

export type VehicleSalesRanking = {
  year: number
  month: number
  period: string
  source_name: string
  source_url: string
  source_note: string
  filters: Record<string, string>
  items: VehicleSalesRankItem[]
}

export type SalesFilterOption = {
  value: string
  label: string
}

export type SalesFilterOptions = {
  vehicle_types: SalesFilterOption[]
  energy_types: SalesFilterOption[]
  manufacturers: SalesFilterOption[]
  brands: Array<{ id: number; name: string }>
}

export function getSalesPeriods() {
  return api<{
    source_name: string
    periods: SalesPeriod[]
  }>('/marketing-ai/public-insight/sales/periods')
}

export function getVehicleSalesRanking(year: number, month: number) {
  return getFilteredVehicleSalesRanking(year, month, {})
}

export function getSalesFilterOptions(year: number, month: number) {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
  })
  return api<SalesFilterOptions>(
    `/marketing-ai/public-insight/sales/filters?${params}`,
  )
}

export function getFilteredVehicleSalesRanking(
  year: number,
  month: number,
  filters: {
    vehicleType?: string
    level?: string
    energyType?: string
    manufacturer?: string
    brandId?: number
  },
) {
  const params = new URLSearchParams({
    year: String(year),
    month: String(month),
    vehicle_type: filters.vehicleType || 'all',
    level: filters.level || '',
    energy_type: filters.energyType || '',
    manufacturer: filters.manufacturer || '',
  })
  if (filters.brandId) params.set('brand_id', String(filters.brandId))
  return api<VehicleSalesRanking>(
    `/marketing-ai/public-insight/sales?${params}`,
  )
}
