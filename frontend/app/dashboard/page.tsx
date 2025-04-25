"use client"

import { useState, useEffect } from "react"
import { trees } from "@/data/trees"
import DashboardLayout from "@/components/dashboard-layout"
import TreeDashboard from "@/components/tree-dashboard"
import { useAuth } from "@/context/auth-context"
import { useRouter } from "next/navigation"

export default function DashboardPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 1000)

    return () => clearTimeout(timer)
  }, [])

  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-[calc(100vh-64px)]">
          <div className="flex flex-col items-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-lg font-medium">Loading tree data...</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <TreeDashboard trees={trees} />
    </DashboardLayout>
  )
}
