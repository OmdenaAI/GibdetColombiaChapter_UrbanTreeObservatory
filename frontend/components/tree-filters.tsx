"use client"

import { Filter, Check, X, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { useState } from "react"

interface TreeFiltersProps {
  uniqueSpecies: string[]
  healthStatuses: string[]
  selectedSpecies: string[]
  selectedHealth: string[]
  setSelectedSpecies: (species: string[]) => void
  setSelectedHealth: (health: string[]) => void
}

export default function TreeFilters({
  uniqueSpecies,
  healthStatuses,
  selectedSpecies,
  selectedHealth,
  setSelectedSpecies,
  setSelectedHealth,
}: TreeFiltersProps) {
  const [isSpeciesOpen, setIsSpeciesOpen] = useState(true)
  const [isHealthOpen, setIsHealthOpen] = useState(true)

  const toggleSpecies = (species: string) => {
    if (selectedSpecies.includes(species)) {
      setSelectedSpecies(selectedSpecies.filter((s) => s !== species))
    } else {
      setSelectedSpecies([...selectedSpecies, species])
    }
  }

  const toggleHealth = (health: string) => {
    if (selectedHealth.includes(health)) {
      setSelectedHealth(selectedHealth.filter((h) => h !== health))
    } else {
      setSelectedHealth([...selectedHealth, health])
    }
  }

  const clearFilters = () => {
    setSelectedSpecies([])
    setSelectedHealth([])
  }

  const getHealthColor = (status: string) => {
    switch (status) {
      case "Healthy":
        return "bg-green-100 text-green-800 hover:bg-green-200 dark:bg-green-900 dark:text-green-100"
      case "Needs Attention":
        return "bg-yellow-100 text-yellow-800 hover:bg-yellow-200 dark:bg-yellow-900 dark:text-yellow-100"
      case "Critical":
        return "bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900 dark:text-red-100"
      default:
        return "bg-gray-100 text-gray-800 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100"
    }
  }

  return (
    <Card className="rounded-xl bg-card shadow-sm border animate-slide-in">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
          {(selectedSpecies.length > 0 || selectedHealth.length > 0) && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-8 px-2 text-xs">
              <X className="mr-1 h-3 w-3" />
              Clear all
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {(selectedSpecies.length > 0 || selectedHealth.length > 0) && (
          <div className="flex flex-wrap gap-2">
            {selectedSpecies.map((species) => (
              <Badge key={species} variant="secondary" className="flex items-center gap-1">
                {species}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => toggleSpecies(species)}
                  className="h-4 w-4 p-0 ml-1 hover:bg-transparent"
                >
                  <X className="h-3 w-3" />
                  <span className="sr-only">Remove {species} filter</span>
                </Button>
              </Badge>
            ))}
            {selectedHealth.map((health) => (
              <Badge key={health} variant="secondary" className={`flex items-center gap-1 ${getHealthColor(health)}`}>
                {health}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => toggleHealth(health)}
                  className="h-4 w-4 p-0 ml-1 hover:bg-transparent"
                >
                  <X className="h-3 w-3" />
                  <span className="sr-only">Remove {health} filter</span>
                </Button>
              </Badge>
            ))}
          </div>
        )}

        <div className="space-y-4">
          <Collapsible open={isSpeciesOpen} onOpenChange={setIsSpeciesOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="flex w-full justify-between p-0 hover:bg-transparent">
                <h4 className="text-sm font-medium">Species</h4>
                <ChevronDown className={`h-4 w-4 transition-transform ${isSpeciesOpen ? "rotate-180" : ""}`} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2">
              <div className="space-y-2 max-h-[200px] overflow-y-auto pr-2">
                {uniqueSpecies.map((species) => (
                  <label key={species} className="flex cursor-pointer items-center gap-2">
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded border ${
                        selectedSpecies.includes(species)
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-input"
                      }`}
                      onClick={() => toggleSpecies(species)}
                    >
                      {selectedSpecies.includes(species) && <Check className="h-3 w-3" />}
                    </div>
                    <span className="text-sm">{species}</span>
                  </label>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Collapsible open={isHealthOpen} onOpenChange={setIsHealthOpen}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="flex w-full justify-between p-0 hover:bg-transparent">
                <h4 className="text-sm font-medium">Health Status</h4>
                <ChevronDown className={`h-4 w-4 transition-transform ${isHealthOpen ? "rotate-180" : ""}`} />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2">
              <div className="space-y-2">
                {healthStatuses.map((health) => (
                  <label key={health} className="flex cursor-pointer items-center gap-2">
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded border ${
                        selectedHealth.includes(health)
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-input"
                      }`}
                      onClick={() => toggleHealth(health)}
                    >
                      {selectedHealth.includes(health) && <Check className="h-3 w-3" />}
                    </div>
                    <span className="text-sm">{health}</span>
                    <div
                      className={`ml-1 h-3 w-3 rounded-full ${
                        health === "Healthy"
                          ? "bg-green-500"
                          : health === "Needs Attention"
                            ? "bg-yellow-500"
                            : "bg-red-500"
                      }`}
                    ></div>
                  </label>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      </CardContent>
    </Card>
  )
}
