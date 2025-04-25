"use client"

import { MapPin } from "lucide-react"
import type { Tree } from "@/types/tree"

interface TreeMarkerProps {
  tree: Tree
  onClick: () => void
}

export default function TreeMarker({ tree, onClick }: TreeMarkerProps) {
  // Calculate position based on coordinates
  const left = `${((tree.location.coordinates.longitude + 180) / 360) * 100}%`
  const top = `${((90 - tree.location.coordinates.latitude) / 180) * 100}%`

  // Determine color based on health status
  const getColor = () => {
    switch (tree.healthStatus) {
      case "Healthy":
        return "text-green-600"
      case "Needs Attention":
        return "text-yellow-500"
      case "Critical":
        return "text-red-500"
      default:
        return "text-gray-500"
    }
  }

  return (
    <button
      className={`absolute -translate-x-1/2 -translate-y-1/2 transform cursor-pointer ${getColor()}`}
      style={{ left, top }}
      onClick={onClick}
      aria-label={`Tree ${tree.id}: ${tree.species}`}
    >
      <MapPin className="h-6 w-6" />
    </button>
  )
}
