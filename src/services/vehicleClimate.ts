export type VehicleClimateSetting = {
  mode: '制热' | '送风' | '制冷'
  temperature: 20 | 22 | 26
}

export function getVehicleClimateSetting(
  currentTemperature: number,
): VehicleClimateSetting {
  if (currentTemperature <= 20) {
    return {
      mode: '制热',
      temperature: 20,
    }
  }

  if (currentTemperature <= 30) {
    return {
      mode: '送风',
      temperature: 22,
    }
  }

  return {
    mode: '制冷',
    temperature: 26,
  }
}
