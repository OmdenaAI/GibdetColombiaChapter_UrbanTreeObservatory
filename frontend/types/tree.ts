export interface Tree {
  id: number
  species: string
  age: number
  height: number
  diameter: number
  location: {
    coordinates: {
      latitude: number
      longitude: number
    }
    address: string
  }
  healthStatus: string
  lastUpdated: string
  environmentalData: {
    soilMoisture: number
    temperature: number
    airQuality: number
  }
  notes: string
}
