"use client"

import { useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
  AreaChart,
  Area,
} from "recharts"
import type { Tree } from "@/types/tree"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface TreeStatsProps {
  trees: Tree[]
}

export default function TreeStats({ trees }: TreeStatsProps) {
  const [chartType, setChartType] = useState<"overview" | "species" | "health" | "trends">("overview")

  // Calculate species distribution
  const speciesCount = trees.reduce(
    (acc, tree) => {
      acc[tree.species] = (acc[tree.species] || 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

  const speciesData = Object.entries(speciesCount).map(([name, value]) => ({
    name,
    value,
  }))

  // Calculate health status distribution
  const healthCount = trees.reduce(
    (acc, tree) => {
      acc[tree.healthStatus] = (acc[tree.healthStatus] || 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

  const healthData = Object.entries(healthCount).map(([name, value]) => ({
    name,
    value,
  }))

  // Calculate age distribution
  const ageRanges = [
    { range: "0-5", count: 0 },
    { range: "6-10", count: 0 },
    { range: "11-20", count: 0 },
    { range: "21-50", count: 0 },
    { range: "51+", count: 0 },
  ]

  trees.forEach((tree) => {
    if (tree.age <= 5) ageRanges[0].count++
    else if (tree.age <= 10) ageRanges[1].count++
    else if (tree.age <= 20) ageRanges[2].count++
    else if (tree.age <= 50) ageRanges[3].count++
    else ageRanges[4].count++
  })

  // Calculate height distribution
  const heightRanges = [
    { range: "0-5m", count: 0 },
    { range: "5-10m", count: 0 },
    { range: "10-15m", count: 0 },
    { range: "15-20m", count: 0 },
    { range: "20m+", count: 0 },
  ]

  trees.forEach((tree) => {
    if (tree.height <= 5) heightRanges[0].count++
    else if (tree.height <= 10) heightRanges[1].count++
    else if (tree.height <= 15) heightRanges[2].count++
    else if (tree.height <= 20) heightRanges[3].count++
    else heightRanges[4].count++
  })

  // Colors for charts
  const SPECIES_COLORS = ["#4CAF50", "#8BC34A", "#CDDC39", "#FFC107", "#FF9800", "#FF5722"]
  const HEALTH_COLORS = {
    Healthy: "#4CAF50",
    "Needs Attention": "#FFC107",
    Critical: "#F44336",
  }

  // Generate trend data (simulated)
  const trendData = [
    { month: "Jan", healthy: 15, attention: 3, critical: 2 },
    { month: "Feb", healthy: 16, attention: 4, critical: 1 },
    { month: "Mar", healthy: 14, attention: 5, critical: 2 },
    { month: "Apr", healthy: 15, attention: 4, critical: 3 },
    { month: "May", healthy: 17, attention: 3, critical: 2 },
    { month: "Jun", healthy: 18, attention: 2, critical: 1 },
    { month: "Jul", healthy: 16, attention: 3, critical: 2 },
    { month: "Aug", healthy: 15, attention: 4, critical: 3 },
    { month: "Sep", healthy: 14, attention: 5, critical: 2 },
    { month: "Oct", healthy: 16, attention: 3, critical: 1 },
    { month: "Nov", healthy: 17, attention: 2, critical: 2 },
    { month: "Dec", healthy: 18, attention: 3, critical: 1 },
  ]

  // Environmental data trends (simulated)
  const environmentalData = [
    { month: "Jan", moisture: 35, temperature: 18, airQuality: 65 },
    { month: "Feb", moisture: 38, temperature: 19, airQuality: 68 },
    { month: "Mar", moisture: 42, temperature: 20, airQuality: 70 },
    { month: "Apr", moisture: 45, temperature: 22, airQuality: 67 },
    { month: "May", moisture: 40, temperature: 24, airQuality: 65 },
    { month: "Jun", moisture: 38, temperature: 26, airQuality: 62 },
    { month: "Jul", moisture: 35, temperature: 27, airQuality: 60 },
    { month: "Aug", moisture: 32, temperature: 26, airQuality: 58 },
    { month: "Sep", moisture: 36, temperature: 25, airQuality: 63 },
    { month: "Oct", moisture: 40, temperature: 23, airQuality: 66 },
    { month: "Nov", moisture: 42, temperature: 20, airQuality: 68 },
    { month: "Dec", moisture: 38, temperature: 18, airQuality: 70 },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h2 className="text-2xl font-semibold">Tree Statistics</h2>
      </div>

      <Tabs value={chartType} onValueChange={(value) => setChartType(value as any)}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div></div> {/* Empty div to maintain layout */}
          <TabsList className="grid grid-cols-2 sm:grid-cols-4 p-1">
            <TabsTrigger value="overview" className="px-3 py-1.5">
              Overview
            </TabsTrigger>
            <TabsTrigger value="species" className="px-3 py-1.5">
              Species
            </TabsTrigger>
            <TabsTrigger value="health" className="px-3 py-1.5">
              Health
            </TabsTrigger>
            <TabsTrigger value="trends" className="px-3 py-1.5">
              Trends
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="overview" className="mt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card className="animate-slide-up overflow-hidden border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Trees</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{trees.length}</div>
                <p className="text-xs text-muted-foreground mt-1">Across {Object.keys(speciesCount).length} species</p>
              </CardContent>
            </Card>
            <Card
              className="animate-slide-up overflow-hidden border-l-4 border-l-secondary"
              style={{ animationDelay: "0.1s" }}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Average Age</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {(trees.reduce((sum, tree) => sum + tree.age, 0) / trees.length).toFixed(1)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Years</p>
              </CardContent>
            </Card>
            <Card
              className="animate-slide-up overflow-hidden border-l-4 border-l-accent"
              style={{ animationDelay: "0.2s" }}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Average Height</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {(trees.reduce((sum, tree) => sum + tree.height, 0) / trees.length).toFixed(1)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Meters</p>
              </CardContent>
            </Card>
            <Card
              className="animate-slide-up overflow-hidden border-l-4 border-l-green-500"
              style={{ animationDelay: "0.3s" }}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Healthy Trees</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">
                  {trees.filter((tree) => tree.healthStatus === "Healthy").length}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  ({((trees.filter((tree) => tree.healthStatus === "Healthy").length / trees.length) * 100).toFixed(0)}
                  %)
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="animate-slide-up" style={{ animationDelay: "0.4s" }}>
              <CardHeader>
                <CardTitle>Species Distribution</CardTitle>
                <CardDescription>Tree count by species</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%" className="mt-2">
                    <PieChart>
                      <Pie
                        data={speciesData}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {speciesData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={SPECIES_COLORS[index % SPECIES_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="animate-slide-up" style={{ animationDelay: "0.5s" }}>
              <CardHeader>
                <CardTitle>Health Status</CardTitle>
                <CardDescription>Tree count by health status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%" className="mt-2">
                    <PieChart>
                      <Pie
                        data={healthData}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {healthData.map((entry) => (
                          <Cell
                            key={`cell-${entry.name}`}
                            fill={HEALTH_COLORS[entry.name as keyof typeof HEALTH_COLORS] || "#9E9E9E"}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="species" className="mt-0">
          <div className="grid grid-cols-1 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Species Distribution</CardTitle>
                <CardDescription>Detailed breakdown of tree species</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%" className="mt-2">
                    <BarChart
                      data={speciesData}
                      margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 60,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" angle={-45} textAnchor="end" height={70} interval={0} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" name="Trees" fill="#4CAF50" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Age Distribution</CardTitle>
                  <CardDescription>Tree count by age range</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%" className="mt-2">
                      <BarChart
                        data={ageRanges}
                        margin={{
                          top: 5,
                          right: 30,
                          left: 20,
                          bottom: 5,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="range" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="count" name="Trees" fill="#8BC34A" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Height Distribution</CardTitle>
                  <CardDescription>Tree count by height range</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%" className="mt-2">
                      <BarChart
                        data={heightRanges}
                        margin={{
                          top: 5,
                          right: 30,
                          left: 20,
                          bottom: 5,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="range" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="count" name="Trees" fill="#66BB6A" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="health" className="mt-0">
          <div className="grid grid-cols-1 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Health Status Distribution</CardTitle>
                <CardDescription>Detailed breakdown of tree health</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%" className="mt-2">
                    <BarChart
                      data={healthData}
                      margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" name="Trees">
                        {healthData.map((entry) => (
                          <Cell
                            key={`cell-${entry.name}`}
                            fill={HEALTH_COLORS[entry.name as keyof typeof HEALTH_COLORS] || "#9E9E9E"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Health by Species</CardTitle>
                  <CardDescription>Health distribution across species</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%" className="mt-2">
                      <BarChart
                        data={Object.entries(speciesCount).map(([species]) => {
                          const speciesTrees = trees.filter((tree) => tree.species === species)
                          const healthy = speciesTrees.filter((tree) => tree.healthStatus === "Healthy").length
                          const needsAttention = speciesTrees.filter(
                            (tree) => tree.healthStatus === "Needs Attention",
                          ).length
                          const critical = speciesTrees.filter((tree) => tree.healthStatus === "Critical").length

                          return {
                            species,
                            healthy,
                            needsAttention,
                            critical,
                          }
                        })}
                        margin={{
                          top: 20,
                          right: 30,
                          left: 20,
                          bottom: 60,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="species" angle={-45} textAnchor="end" height={70} interval={0} />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="healthy" name="Healthy" stackId="a" fill="#4CAF50" />
                        <Bar dataKey="needsAttention" name="Needs Attention" stackId="a" fill="#FFC107" />
                        <Bar dataKey="critical" name="Critical" stackId="a" fill="#F44336" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Environmental Factors</CardTitle>
                  <CardDescription>Average environmental data by health status</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%" className="mt-2">
                      <BarChart
                        data={["Healthy", "Needs Attention", "Critical"].map((status) => {
                          const statusTrees = trees.filter((tree) => tree.healthStatus === status)
                          const avgMoisture =
                            statusTrees.reduce((sum, tree) => sum + tree.environmentalData.soilMoisture, 0) /
                            statusTrees.length
                          const avgTemp =
                            statusTrees.reduce((sum, tree) => sum + tree.environmentalData.temperature, 0) /
                            statusTrees.length
                          const avgAir =
                            statusTrees.reduce((sum, tree) => sum + tree.environmentalData.airQuality, 0) /
                            statusTrees.length

                          return {
                            status,
                            moisture: avgMoisture || 0,
                            temperature: avgTemp || 0,
                            airQuality: avgAir || 0,
                          }
                        })}
                        margin={{
                          top: 20,
                          right: 30,
                          left: 20,
                          bottom: 5,
                        }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="status" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="moisture" name="Soil Moisture %" fill="#2196F3" />
                        <Bar dataKey="temperature" name="Temperature °C" fill="#FF5722" />
                        <Bar dataKey="airQuality" name="Air Quality Index" fill="#9C27B0" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="trends" className="mt-0">
          <div className="grid grid-cols-1 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Health Status Trends</CardTitle>
                <CardDescription>Monthly trends in tree health status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%" className="mt-2">
                    <LineChart
                      data={trendData}
                      margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="healthy" name="Healthy" stroke="#4CAF50" activeDot={{ r: 8 }} />
                      <Line type="monotone" dataKey="attention" name="Needs Attention" stroke="#FFC107" />
                      <Line type="monotone" dataKey="critical" name="Critical" stroke="#F44336" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Environmental Data Trends</CardTitle>
                <CardDescription>Monthly environmental data measurements</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%" className="mt-2">
                    <AreaChart
                      data={environmentalData}
                      margin={{
                        top: 10,
                        right: 30,
                        left: 0,
                        bottom: 0,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="moisture"
                        name="Soil Moisture %"
                        stroke="#2196F3"
                        fill="#2196F3"
                        fillOpacity={0.3}
                      />
                      <Area
                        type="monotone"
                        dataKey="temperature"
                        name="Temperature °C"
                        stroke="#FF5722"
                        fill="#FF5722"
                        fillOpacity={0.3}
                      />
                      <Area
                        type="monotone"
                        dataKey="airQuality"
                        name="Air Quality Index"
                        stroke="#9C27B0"
                        fill="#9C27B0"
                        fillOpacity={0.3}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
