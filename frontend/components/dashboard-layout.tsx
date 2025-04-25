"use client"

import type React from "react"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Leaf,
  LayoutDashboard,
  Map,
  BarChart3,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  Moon,
  Sun,
  Info,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "next-themes"
import { useAuth } from "@/context/auth-context"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { user, logout } = useAuth()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen)
  }

  const closeSidebar = () => {
    setIsSidebarOpen(false)
  }

  const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="h-5 w-5" /> },
    { href: "/map", label: "Map View", icon: <Map className="h-5 w-5" /> },
    { href: "/analytics", label: "Analytics", icon: <BarChart3 className="h-5 w-5" /> },
    { href: "/reports", label: "Reports", icon: <FileText className="h-5 w-5" /> },
    { href: "/about", label: "About", icon: <Info className="h-5 w-5" /> },
    { href: "/settings", label: "Settings", icon: <Settings className="h-5 w-5" /> },
  ]

  if (!mounted) {
    return null
  }

  const getPageTitle = (path: string) => {
    if (path.includes("/dashboard")) return "Dashboard"
    if (path.includes("/map")) return "Map View"
    if (path.includes("/analytics")) return "Analytics"
    if (path.includes("/reports")) return "Reports"
    if (path.includes("/about")) return "About"
    if (path.includes("/settings")) return "Settings"
    return "Tree Observatory"
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile sidebar backdrop */}
      {isSidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={closeSidebar} aria-hidden="true"></div>
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-card shadow-lg transition-transform duration-200 ease-in-out md:relative md:translate-x-0 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b p-4">
            <Link href="/dashboard" className="flex items-center gap-2" onClick={closeSidebar}>
              <Leaf className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Tree Observatory</span>
            </Link>
            <Button variant="ghost" size="icon" onClick={closeSidebar} className="md:hidden">
              <X className="h-5 w-5" />
              <span className="sr-only">Close sidebar</span>
            </Button>
          </div>

          <nav className="flex-1 overflow-auto p-4">
            <ul className="space-y-4">
              {navItems.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={closeSidebar}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
                      pathname === item.href
                        ? "bg-primary text-primary-foreground font-medium"
                        : "hover:bg-muted text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div className="border-t p-4">
            <div className="flex items-center gap-3 rounded-lg px-3 py-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                className="mr-2"
              >
                {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
                <span className="sr-only">Toggle theme</span>
              </Button>

              {user ? (
                <div className="flex flex-1 items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src="/placeholder.svg?height=32&width=32" alt={user.name} />
                      <AvatarFallback>{user.name.charAt(0)}</AvatarFallback>
                    </Avatar>
                    <div className="text-sm">
                      <p className="font-medium">{user.name}</p>
                      <p className="text-xs text-muted-foreground">{user.role}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={logout}>
                    <LogOut className="h-5 w-5" />
                    <span className="sr-only">Log out</span>
                  </Button>
                </div>
              ) : (
                <Link
                  href="/login"
                  className="flex w-full items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground"
                >
                  <User className="h-5 w-5" />
                  <span>Log in</span>
                </Link>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b bg-card shadow-sm">
          <div className="flex h-16 items-center justify-between px-4">
            <Button variant="ghost" size="icon" onClick={toggleSidebar} className="md:hidden">
              <Menu className="h-6 w-6" />
              <span className="sr-only">Toggle sidebar</span>
            </Button>

            <div className="flex items-center gap-2 md:hidden">
              <Leaf className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Tree Observatory</span>
            </div>

            <div className="hidden md:block">
              <h1 className="text-lg font-medium">{getPageTitle(pathname)}</h1>
            </div>

            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                className="hidden md:flex"
              >
                {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
                <span className="sr-only">Toggle theme</span>
              </Button>

              {user ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="flex items-center gap-2 rounded-lg">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src="/placeholder.svg?height=32&width=32" alt={user.name} />
                        <AvatarFallback>{user.name.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <div className="hidden text-left md:block">
                        <p className="text-sm font-medium">{user.name}</p>
                        <p className="text-xs text-muted-foreground">{user.role}</p>
                      </div>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>
                      <User className="mr-2 h-4 w-4" />
                      Profile
                    </DropdownMenuItem>
                    <DropdownMenuItem>
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={logout}>
                      <LogOut className="mr-2 h-4 w-4" />
                      Log out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <Link
                  href="/login"
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-primary-foreground"
                >
                  <User className="h-5 w-5" />
                  <span>Log in</span>
                </Link>
              )}
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto bg-background">{children}</main>
      </div>
    </div>
  )
}
