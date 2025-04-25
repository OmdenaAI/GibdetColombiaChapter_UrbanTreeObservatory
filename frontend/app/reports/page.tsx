"use client"

import { useState } from "react"
import { trees } from "@/data/trees"
import DashboardLayout from "@/components/dashboard-layout"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Calendar, Download, FileText, Printer, Share2 } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

export default function ReportsPage() {
  const [reportType, setReportType] = useState<"summary" | "health" | "species" | "environmental">("summary")
  const [timeframe, setTimeframe] = useState<"daily" | "weekly" | "monthly" | "yearly">("monthly")

  const getHealthStatusClass = (status: string) => {
    switch (status) {
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

  const handleExport = (format: string) => {
    // Simulate export functionality
    alert(`Exporting ${reportType} report in ${format} format...`)
  }

  const handlePrint = () => {
    // Simulate print functionality
    alert("Preparing report for printing...")
  }

  const handleShare = () => {
    // Simulate share functionality
    alert("Opening share options...")
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 animate-fade-in">
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Reports</h1>
            <p className="mt-2 text-muted-foreground">
              Generate and export detailed reports about Columbia's urban forest
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handlePrint}>
              <Printer className="mr-2 h-4 w-4" />
              Print
            </Button>
            <Button variant="outline" onClick={handleShare}>
              <Share2 className="mr-2 h-4 w-4" />
              Share
            </Button>
            <div className="relative">
              <Button variant="default">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="lg:col-span-1 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Report Options</CardTitle>
                <CardDescription>Configure your report</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="mb-2 text-sm font-medium">Report Type</h3>
                  <Tabs
                    defaultValue="summary"
                    value={reportType}
                    onValueChange={(value) => setReportType(value as any)}
                    className="w-full"
                  >
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="summary">Summary</TabsTrigger>
                      <TabsTrigger value="health">Health</TabsTrigger>
                    </TabsList>
                    <TabsList className="grid w-full grid-cols-2 mt-1">
                      <TabsTrigger value="species">Species</TabsTrigger>
                      <TabsTrigger value="environmental">Environmental</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                <div>
                  <h3 className="mb-2 text-sm font-medium">Time Frame</h3>
                  <Tabs
                    defaultValue="monthly"
                    value={timeframe}
                    onValueChange={(value) => setTimeframe(value as any)}
                    className="w-full"
                  >
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="daily">Daily</TabsTrigger>
                      <TabsTrigger value="weekly">Weekly</TabsTrigger>
                    </TabsList>
                    <TabsList className="grid w-full grid-cols-2 mt-1">
                      <TabsTrigger value="monthly">Monthly</TabsTrigger>
                      <TabsTrigger value="yearly">Yearly</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                <div>
                  <h3 className="mb-2 text-sm font-medium">Date Range</h3>
                  <Button variant="outline" className="w-full justify-start text-left font-normal">
                    <Calendar className="mr-2 h-4 w-4" />
                    <span>November 2023</span>
                  </Button>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full">
                  <FileText className="mr-2 h-4 w-4" />
                  Generate Report
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Export Options</CardTitle>
                <CardDescription>Available formats</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Button variant="outline" className="w-full justify-start" onClick={() => handleExport("pdf")}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export as PDF
                  </Button>
                  <Button variant="outline" className="w-full justify-start" onClick={() => handleExport("csv")}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export as CSV
                  </Button>
                  <Button variant="outline" className="w-full justify-start" onClick={() => handleExport("excel")}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export as Excel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-3">
            <Card>
              <CardHeader>
                <CardTitle>
                  {reportType.charAt(0).toUpperCase() + reportType.slice(1)} Report -{" "}
                  {timeframe.charAt(0).toUpperCase() + timeframe.slice(1)}
                </CardTitle>
                <CardDescription>
                  Generated on {new Date().toLocaleDateString()} for Columbia Tree Observatory
                </CardDescription>
              </CardHeader>
              <Tabs defaultValue="summary" value={reportType}>
                <CardContent>
                  <TabsContent value="summary" className="mt-0">
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Total Trees</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-3xl font-bold">{trees.length}</div>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Species Count</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-3xl font-bold">{new Set(trees.map((t) => t.species)).size}</div>
                          </CardContent>
                        </Card>
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium">Health Status</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="text-3xl font-bold">
                              {Math.round(
                                (trees.filter((t) => t.healthStatus === "Healthy").length / trees.length) * 100,
                              )}
                              %
                            </div>
                            <p className="text-xs text-muted-foreground">Healthy trees</p>
                          </CardContent>
                        </Card>
                      </div>

                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Category</TableHead>
                            <TableHead>Count</TableHead>
                            <TableHead>Percentage</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          <TableRow>
                            <TableCell>Healthy Trees</TableCell>
                            <TableCell>{trees.filter((t) => t.healthStatus === "Healthy").length}</TableCell>
                            <TableCell>
                              {Math.round(
                                (trees.filter((t) => t.healthStatus === "Healthy").length / trees.length) * 100,
                              )}
                              %
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Trees Needing Attention</TableCell>
                            <TableCell>{trees.filter((t) => t.healthStatus === "Needs Attention").length}</TableCell>
                            <TableCell>
                              {Math.round(
                                (trees.filter((t) => t.healthStatus === "Needs Attention").length / trees.length) * 100,
                              )}
                              %
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Critical Trees</TableCell>
                            <TableCell>{trees.filter((t) => t.healthStatus === "Critical").length}</TableCell>
                            <TableCell>
                              {Math.round(
                                (trees.filter((t) => t.healthStatus === "Critical").length / trees.length) * 100,
                              )}
                              %
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Average Tree Age</TableCell>
                            <TableCell colSpan={2}>
                              {Math.round(trees.reduce((sum, t) => sum + t.age, 0) / trees.length)} years
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell>Average Tree Height</TableCell>
                            <TableCell colSpan={2}>
                              {(trees.reduce((sum, t) => sum + t.height, 0) / trees.length).toFixed(1)} meters
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>

                  <TabsContent value="health" className="mt-0">
                    <div className="space-y-6">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>ID</TableHead>
                            <TableHead>Species</TableHead>
                            <TableHead>Health Status</TableHead>
                            <TableHead>Last Updated</TableHead>
                            <TableHead>Notes</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {trees.map((tree) => (
                            <TableRow key={tree.id}>
                              <TableCell>{tree.id}</TableCell>
                              <TableCell>{tree.species}</TableCell>
                              <TableCell>
                                <Badge className={getHealthStatusClass(tree.healthStatus)}>{tree.healthStatus}</Badge>
                              </TableCell>
                              <TableCell>{tree.lastUpdated}</TableCell>
                              <TableCell className="max-w-xs truncate">{tree.notes}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>

                  <TabsContent value="species" className="mt-0">
                    <div className="space-y-6">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Species</TableHead>
                            <TableHead>Count</TableHead>
                            <TableHead>Average Age</TableHead>
                            <TableHead>Average Height</TableHead>
                            <TableHead>Health Distribution</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Array.from(new Set(trees.map((t) => t.species))).map((species) => {
                            const speciesTrees = trees.filter((t) => t.species === species)
                            const avgAge = Math.round(
                              speciesTrees.reduce((sum, t) => sum + t.age, 0) / speciesTrees.length,
                            )
                            const avgHeight = (
                              speciesTrees.reduce((sum, t) => sum + t.height, 0) / speciesTrees.length
                            ).toFixed(1)
                            const healthy = speciesTrees.filter((t) => t.healthStatus === "Healthy").length
                            const needsAttention = speciesTrees.filter(
                              (t) => t.healthStatus === "Needs Attention",
                            ).length
                            const critical = speciesTrees.filter((t) => t.healthStatus === "Critical").length

                            return (
                              <TableRow key={species as string}>
                                <TableCell>{species}</TableCell>
                                <TableCell>{speciesTrees.length}</TableCell>
                                <TableCell>{avgAge} years</TableCell>
                                <TableCell>{avgHeight} meters</TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                                      <div
                                        className="bg-green-500 h-2.5 rounded-full"
                                        style={{ width: `${(healthy / speciesTrees.length) * 100}%` }}
                                      ></div>
                                    </div>
                                    <span className="text-xs">
                                      {Math.round((healthy / speciesTrees.length) * 100)}%
                                    </span>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>

                  <TabsContent value="environmental" className="mt-0">
                    <div className="space-y-6">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>ID</TableHead>
                            <TableHead>Species</TableHead>
                            <TableHead>Soil Moisture</TableHead>
                            <TableHead>Temperature</TableHead>
                            <TableHead>Air Quality</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {trees.map((tree) => (
                            <TableRow key={tree.id}>
                              <TableCell>{tree.id}</TableCell>
                              <TableCell>{tree.species}</TableCell>
                              <TableCell>{tree.environmentalData.soilMoisture}%</TableCell>
                              <TableCell>{tree.environmentalData.temperature}°C</TableCell>
                              <TableCell>{tree.environmentalData.airQuality} AQI</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                </CardContent>
              </Tabs>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
