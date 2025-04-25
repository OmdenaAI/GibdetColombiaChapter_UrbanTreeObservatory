"use client"

import { X, Droplets, Thermometer, Wind, Calendar, MapPin, Ruler, Leaf, CircleDot } from "lucide-react"
import type { Tree } from "@/types/tree"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

interface TreeDetailProps {
  tree: Tree
  onClose: () => void
}

export default function TreeDetail({ tree, onClose }: TreeDetailProps) {
  // Determine health status color
  const getHealthColor = () => {
    switch (tree.healthStatus) {
      case "Healthy":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
      case "Needs Attention":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100"
      case "Critical":
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
    }
  }

  return (
    <Card className="animate-slide-up shadow-lg overflow-hidden">
      <CardHeader className="pb-2 bg-muted/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Leaf className="h-5 w-5 text-primary" />
            Tree #{tree.id}
          </CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 p-4">
        <div className="aspect-video overflow-hidden rounded-lg bg-muted">
          <img
            src={`/placeholder.svg?height=200&width=400&text=Tree+${tree.id}`}
            alt={`Tree ${tree.id}`}
            className="h-full w-full object-cover"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Species</p>
            <p className="font-medium flex items-center gap-1">
              <CircleDot className="h-3 w-3 text-primary" />
              {tree.species}
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Age</p>
            <p className="font-medium flex items-center gap-1">
              <Calendar className="h-3 w-3 text-primary" />
              {tree.age} years
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Height</p>
            <p className="font-medium flex items-center gap-1">
              <Ruler className="h-3 w-3 text-primary" />
              {tree.height} meters
            </p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Diameter</p>
            <p className="font-medium flex items-center gap-1">
              <CircleDot className="h-3 w-3 text-primary" />
              {tree.diameter} cm
            </p>
          </div>
        </div>

        <Separator />

        <div>
          <p className="text-xs text-muted-foreground mb-1">Location</p>
          <div className="flex items-center gap-1">
            <MapPin className="h-3 w-3 text-primary" />
            <p className="font-medium">{tree.location.address}</p>
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Coordinates: {tree.location.coordinates.latitude.toFixed(6)},{" "}
            {tree.location.coordinates.longitude.toFixed(6)}
          </div>
        </div>

        <div>
          <Badge className={`${getHealthColor()} px-3 py-1`}>{tree.healthStatus}</Badge>
        </div>

        <div>
          <p className="mb-2 text-xs text-muted-foreground">Environmental Data</p>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-1 rounded-md bg-muted p-2">
              <Droplets className="h-4 w-4 text-blue-500" />
              <span className="text-xs">{tree.environmentalData.soilMoisture}% moisture</span>
            </div>
            <div className="flex items-center gap-1 rounded-md bg-muted p-2">
              <Thermometer className="h-4 w-4 text-red-500" />
              <span className="text-xs">{tree.environmentalData.temperature}°C</span>
            </div>
            <div className="flex items-center gap-1 rounded-md bg-muted p-2">
              <Wind className="h-4 w-4 text-gray-500" />
              <span className="text-xs">{tree.environmentalData.airQuality} AQI</span>
            </div>
            <div className="flex items-center gap-1 rounded-md bg-muted p-2">
              <Calendar className="h-4 w-4 text-green-500" />
              <span className="text-xs">Updated: {tree.lastUpdated}</span>
            </div>
          </div>
        </div>

        <div className="text-xs">
          <p className="font-medium mb-1 text-muted-foreground">Notes:</p>
          <p className="bg-muted/50 p-2 rounded-md">{tree.notes}</p>
        </div>
      </CardContent>
      <CardFooter className="flex justify-end gap-2 bg-muted/30 py-3">
        <Button variant="outline" size="sm">
          Edit
        </Button>
        <Button size="sm">Report Issue</Button>
      </CardFooter>
    </Card>
  )
}
