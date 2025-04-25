"use client"

import type React from "react"

import { createContext, useContext, useState, useEffect } from "react"

interface User {
  name: string
  email: string
  role: "admin" | "user" | "guest"
}

interface AuthContextType {
  user: User | null
  login: (user: User) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: () => {},
})

export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for saved user in localStorage
    const savedUser = localStorage.getItem("treeObservatoryUser")
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser))
      } catch (error) {
        console.error("Failed to parse saved user:", error)
        localStorage.removeItem("treeObservatoryUser")
      }
    }
    setLoading(false)
  }, [])

  const login = (userData: User) => {
    setUser(userData)
    localStorage.setItem("treeObservatoryUser", JSON.stringify(userData))
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem("treeObservatoryUser")
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}
