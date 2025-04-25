"use client"

import { useState } from "react"
import { Search, Leaf, BarChart3, Map, Download, Filter, FileText } from "lucide-react"
import type { Tree } from "@/types/tree"
import TreeMap from "@/components/tree-map"
import TreeList from "@/components/tree-list"
import TreeStats from "@/components/tree-stats"
import TreeFilters from "@/components/tree-filters"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

interface TreeDashboardProps {
  trees: Tree[]
}

export default function TreeDashboard({ trees }: TreeDashboardProps) {
  const [view, setView] = useState<"map" | "list" | "stats">("map")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSpecies, setSelectedSpecies] = useState<string[]>([])
  const [selectedHealth, setSelectedHealth] = useState<string[]>([])
  const [showFilters, setShowFilters] = useState(false)

  const filteredTrees = trees.filter((tree) => {
    const matchesSearch =
      tree.id.toString().includes(searchQuery) ||
      tree.species.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tree.location.address.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesSpecies = selectedSpecies.length === 0 || selectedSpecies.includes(tree.species)
    const matchesHealth = selectedHealth.length === 0 || selectedHealth.includes(tree.healthStatus)

    return matchesSearch && matchesSpecies && matchesHealth
  })

  const uniqueSpecies = Array.from(new Set(trees.map((tree) => tree.species)))
  const healthStatuses = ["Healthy", "Needs Attention", "Critical"]

  const toggleFilters = () => {
    setShowFilters(!showFilters)
  }

  const handleExport = (format: string) => {
    // Simulate export functionality
    alert(`Exporting data in ${format} format...`)
  }

  return (
    <div className="container mx-auto px-4 py-8 animate-fade-in">
      <header className="mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Columbia Tree Observatory</h1>
            <p className="mt-2 text-muted-foreground">Monitoring and preserving our urban forest ecosystem</p>
          </div>
          <div className="flex items-center gap-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="flex items-center gap-2">
                  <Download className="h-4 w-4" />
                  <span>Export</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => handleExport("csv")}>
                  <FileText className="mr-2 h-4 w-4" />
                  Export as CSV
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport("json")}>
                  <FileText className="mr-2 h-4 w-4" />
                  Export as JSON
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport("pdf")}>
                  <FileText className="mr-2 h-4 w-4" />
                  Export as PDF
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="outline" onClick={toggleFilters} className="md:hidden">
              <Filter className="h-4 w-4" />
              <span className="sr-only">Filters</span>
            </Button>
          </div>
        </div>
      </header>

      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search by ID, species, or location..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <Tabs defaultValue="map" className="w-full md:w-auto" onValueChange={(value) => setView(value as any)}>
          <TabsList className="grid w-full grid-cols-3 md:w-auto">
            <TabsTrigger value="map" className="flex items-center gap-2 px-4">
              <Map className="h-4 w-4" />
              <span className="hidden md:inline">Map</span>
            </TabsTrigger>
            <TabsTrigger value="list" className="flex items-center gap-2 px-4">
              <Leaf className="h-4 w-4" />
              <span className="hidden md:inline">List</span>
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex items-center gap-2 px-4">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden md:inline">Stats</span>
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Filters sidebar - desktop */}
        <div className="hidden lg:block lg:col-span-1">
          <TreeFilters
            uniqueSpecies={uniqueSpecies}
            healthStatuses={healthStatuses}
            selectedSpecies={selectedSpecies}
            selectedHealth={selectedHealth}
            setSelectedSpecies={setSelectedSpecies}
            setSelectedHealth={setSelectedHealth}
          />
        </div>

        {/* Filters sidebar - mobile */}
        {showFilters && (
          <div className="lg:hidden">
            <Card className="p-4">
              <TreeFilters
                uniqueSpecies={uniqueSpecies}
                healthStatuses={healthStatuses}
                selectedSpecies={selectedSpecies}
                selectedHealth={selectedHealth}
                setSelectedSpecies={setSelectedSpecies}
                setSelectedHealth={setSelectedHealth}
              />
            </Card>
          </div>
        )}

        <div className="lg:col-span-3">
          <Tabs defaultValue="map" value={view}>
            <TabsContent value="map" className="mt-0">
              <Card className="overflow-hidden">
                <TreeMap trees={filteredTrees} />
              </Card>
            </TabsContent>
            <TabsContent value="list" className="mt-0">
              <Card>
                <TreeList trees={filteredTrees} />
              </Card>
            </TabsContent>
            <TabsContent value="stats" className="mt-0">
              <Card className="p-6">
                <TreeStats trees={filteredTrees} />
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
