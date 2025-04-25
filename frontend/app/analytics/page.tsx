"use client"

import { trees } from "@/data/trees"
import DashboardLayout from "@/components/dashboard-layout"
import TreeStats from "@/components/tree-stats"
import { Card } from "@/components/ui/card"

export default function AnalyticsPage() {
  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 animate-fade-in">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Tree Analytics</h1>
          <p className="mt-2 text-muted-foreground">Comprehensive data analysis of Columbia's urban forest</p>
        </div>

        <Card className="p-6">
          <TreeStats trees={trees} />
        </Card>
      </div>
    </DashboardLayout>
  )
}
