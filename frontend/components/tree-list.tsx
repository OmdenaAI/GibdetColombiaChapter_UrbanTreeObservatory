"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, ArrowUpDown } from "lucide-react"
import type { Tree } from "@/types/tree"
import TreeDetail from "@/components/tree-detail"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

interface TreeListProps {
  trees: Tree[]
}

export default function TreeList({ trees }: TreeListProps) {
  const [expandedTree, setExpandedTree] = useState<number | null>(null)
  const [sortField, setSortField] = useState<keyof Tree | "location.address">("id")
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc")

  const handleSort = (field: keyof Tree | "location.address") => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortDirection("asc")
    }
  }

  const sortedTrees = [...trees].sort((a, b) => {
    let valueA, valueB

    if (sortField === "location.address") {
      valueA = a.location.address
      valueB = b.location.address
    } else {
      valueA = a[sortField]
      valueB = b[sortField]
    }

    if (typeof valueA === "string" && typeof valueB === "string") {
      return sortDirection === "asc" ? valueA.localeCompare(valueB) : valueB.localeCompare(valueA)
    } else {
      return sortDirection === "asc" ? (valueA as number) - (valueB as number) : (valueB as number) - (valueA as number)
    }
  })

  const getSortIcon = (field: keyof Tree | "location.address") => {
    if (sortField !== field) return <ArrowUpDown className="h-4 w-4" />
    return sortDirection === "asc" ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
  }

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

  return (
    <div className="animate-fade-in">
      <div className="rounded-md border shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              <TableHead className="w-[80px]">
                <Button
                  variant="ghost"
                  className="p-0 hover:bg-transparent font-medium"
                  onClick={() => handleSort("id")}
                >
                  <span>ID</span>
                  {getSortIcon("id")}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  className="p-0 hover:bg-transparent font-medium"
                  onClick={() => handleSort("species")}
                >
                  <span>Species</span>
                  {getSortIcon("species")}
                </Button>
              </TableHead>
              <TableHead className="hidden md:table-cell">
                <Button
                  variant="ghost"
                  className="p-0 hover:bg-transparent font-medium"
                  onClick={() => handleSort("location.address")}
                >
                  <span>Location</span>
                  {getSortIcon("location.address")}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  className="p-0 hover:bg-transparent font-medium"
                  onClick={() => handleSort("healthStatus")}
                >
                  <span>Health</span>
                  {getSortIcon("healthStatus")}
                </Button>
              </TableHead>
              <TableHead className="hidden md:table-cell">
                <Button
                  variant="ghost"
                  className="p-0 hover:bg-transparent font-medium"
                  onClick={() => handleSort("height")}
                >
                  <span>Height (m)</span>
                  {getSortIcon("height")}
                </Button>
              </TableHead>
              <TableHead className="hidden md:table-cell">
                <Button
                  variant="ghost"
                  className="p-0 hover:bg-transparent font-medium"
                  onClick={() => handleSort("age")}
                >
                  <span>Age (years)</span>
                  {getSortIcon("age")}
                </Button>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedTrees.map((tree) => (
              <TableRow
                key={tree.id}
                className="cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => setExpandedTree(expandedTree === tree.id ? null : tree.id)}
              >
                <TableCell className="font-medium">{tree.id}</TableCell>
                <TableCell>{tree.species}</TableCell>
                <TableCell className="hidden md:table-cell">{tree.location.address}</TableCell>
                <TableCell>
                  <Badge className={getHealthStatusClass(tree.healthStatus)}>{tree.healthStatus}</Badge>
                </TableCell>
                <TableCell className="hidden md:table-cell">{tree.height}</TableCell>
                <TableCell className="hidden md:table-cell">{tree.age}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {expandedTree !== null && (
        <div className="mt-4">
          <TreeDetail tree={trees.find((t) => t.id === expandedTree)!} onClose={() => setExpandedTree(null)} />
        </div>
      )}
    </div>
  )
}
