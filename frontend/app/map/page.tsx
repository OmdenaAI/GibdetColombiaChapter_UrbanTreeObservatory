"use client"

import { useState } from "react"
import { trees } from "@/data/trees"
import DashboardLayout from "@/components/dashboard-layout"
import TreeMap from "@/components/tree-map"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import TreeFilters from "@/components/tree-filters"

export default function MapPage() {
  const [selectedSpecies, setSelectedSpecies] = useState<string[]>([])
  const [selectedHealth, setSelectedHealth] = useState<string[]>([])
  const [mapView, setMapView] = useState<"standard" | "satellite" | "terrain">("standard")

  const filteredTrees = trees.filter((tree) => {
    const matchesSpecies = selectedSpecies.length === 0 || selectedSpecies.includes(tree.species)
    const matchesHealth = selectedHealth.length === 0 || selectedHealth.includes(tree.healthStatus)
    return matchesSpecies && matchesHealth
  })

  const uniqueSpecies = Array.from(new Set(trees.map((tree) => tree.species)))
  const healthStatuses = ["Healthy", "Needs Attention", "Critical"]

  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 animate-fade-in">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Interactive Tree Map</h1>
          <p className="mt-2 text-muted-foreground">Explore the urban forest of Columbia with our interactive map</p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="lg:col-span-1 space-y-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Map Options</CardTitle>
                <CardDescription>Customize your map view</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="standard" value={mapView} onValueChange={(value) => setMapView(value as any)}>
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="standard">Standard</TabsTrigger>
                    <TabsTrigger value="satellite">Satellite</TabsTrigger>
                    <TabsTrigger value="terrain">Terrain</TabsTrigger>
                  </TabsList>
                </Tabs>
              </CardContent>
            </Card>

            <TreeFilters
              uniqueSpecies={uniqueSpecies}
              healthStatuses={healthStatuses}
              selectedSpecies={selectedSpecies}
              selectedHealth={selectedHealth}
              setSelectedSpecies={setSelectedSpecies}
              setSelectedHealth={setSelectedHealth}
            />

            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Map Legend</CardTitle>
                <CardDescription>Tree health indicators</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-green-500"></div>
                    <span className="text-sm">Healthy</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
                    <span className="text-sm">Needs Attention</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-red-500"></div>
                    <span className="text-sm">Critical</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Map Statistics</CardTitle>
                <CardDescription>Current view data</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Total trees:</span>
                    <span className="text-sm font-medium">{filteredTrees.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Healthy:</span>
                    <span className="text-sm font-medium">
                      {filteredTrees.filter((t) => t.healthStatus === "Healthy").length}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Needs attention:</span>
                    <span className="text-sm font-medium">
                      {filteredTrees.filter((t) => t.healthStatus === "Needs Attention").length}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Critical:</span>
                    <span className="text-sm font-medium">
                      {filteredTrees.filter((t) => t.healthStatus === "Critical").length}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-3">
            <Card className="overflow-hidden">
              <TreeMap trees={filteredTrees} />
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
