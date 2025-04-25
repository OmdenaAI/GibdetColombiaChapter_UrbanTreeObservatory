"use client"

import { useState, useEffect, useRef } from "react"
import dynamic from "next/dynamic"
import type { Tree } from "@/types/tree"
import TreeDetail from "@/components/tree-detail"
import { Skeleton } from "@/components/ui/skeleton"

// Dynamically import Leaflet components with no SSR
const MapContainer = dynamic(() => import("react-leaflet").then((mod) => mod.MapContainer), { ssr: false })
const TileLayer = dynamic(() => import("react-leaflet").then((mod) => mod.TileLayer), { ssr: false })
const Marker = dynamic(() => import("react-leaflet").then((mod) => mod.Marker), { ssr: false })
const Popup = dynamic(() => import("react-leaflet").then((mod) => mod.Popup), { ssr: false })

interface TreeMapProps {
  trees: Tree[]
}

export default function TreeMap({ trees }: TreeMapProps) {
  const [selectedTree, setSelectedTree] = useState<Tree | null>(null)
  const [isClient, setIsClient] = useState(false)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [leaflet, setLeaflet] = useState<any>(null)
  const mapRef = useRef(null)

  useEffect(() => {
    setIsClient(true)
    // Simulate map loading
    const timer = setTimeout(() => {
      setMapLoaded(true)
    }, 1000)

    // Import Leaflet on the client side
    import("leaflet").then((L) => {
      setLeaflet(L)

      // Fix the default icon issue in Leaflet
      delete L.Icon.Default.prototype._getIconUrl
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
      })
    })

    return () => clearTimeout(timer)
  }, [])

  if (!isClient || !leaflet) {
    return (
      <div className="h-[600px] w-full bg-muted flex items-center justify-center">
        <Skeleton className="h-full w-full" />
      </div>
    )
  }

  if (!mapLoaded) {
    return (
      <div className="h-[600px] w-full bg-muted flex items-center justify-center rounded-lg border">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading interactive map...</p>
        </div>
      </div>
    )
  }

  // Create custom icons for different tree health statuses
  const healthyIcon = leaflet.icon({
    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  })

  const attentionIcon = leaflet.icon({
    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-yellow.png",
    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  })

  const criticalIcon = leaflet.icon({
    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41],
  })

  // Get icon based on tree health status
  const getTreeIcon = (status: string) => {
    switch (status) {
      case "Healthy":
        return healthyIcon
      case "Needs Attention":
        return attentionIcon
      case "Critical":
        return criticalIcon
      default:
        return healthyIcon
    }
  }

  // Calculate map center (average of all tree coordinates)
  const center =
    trees.length > 0
      ? [
          trees.reduce((sum, tree) => sum + tree.location.coordinates.latitude, 0) / trees.length,
          trees.reduce((sum, tree) => sum + tree.location.coordinates.longitude, 0) / trees.length,
        ]
      : [4.624335, -74.063644] // Default center (Bogotá)

  return (
    <div className="relative h-[600px] w-full rounded-lg overflow-hidden border">
      <MapContainer
        center={center as [number, number]}
        zoom={14}
        scrollWheelZoom={true}
        style={{ height: "100%", width: "100%" }}
        ref={mapRef}
        className="z-10"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {trees.map((tree) => (
          <Marker
            key={tree.id}
            position={[tree.location.coordinates.latitude, tree.location.coordinates.longitude]}
            icon={getTreeIcon(tree.healthStatus)}
            eventHandlers={{
              click: () => {
                setSelectedTree(tree)
              },
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold">Tree #{tree.id}</p>
                <p>{tree.species}</p>
                <p>Health: {tree.healthStatus}</p>
                <button className="mt-2 text-primary hover:underline" onClick={() => setSelectedTree(tree)}>
                  View Details
                </button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Tree detail panel */}
      {selectedTree && (
        <div className="absolute bottom-4 right-4 w-full max-w-sm z-[1000]">
          <TreeDetail tree={selectedTree} onClose={() => setSelectedTree(null)} />
        </div>
      )}

      {/* Map legend */}
      <div className="absolute bottom-4 left-4 bg-card p-3 rounded-lg shadow-md z-[1000] border">
        <h4 className="text-sm font-medium mb-2">Tree Health</h4>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-xs">Healthy</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <span className="text-xs">Needs Attention</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span className="text-xs">Critical</span>
          </div>
        </div>
      </div>
    </div>
  )
}
