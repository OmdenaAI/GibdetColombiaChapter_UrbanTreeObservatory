"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Leaf, LogIn } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/context/auth-context"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const router = useRouter()
  const { login } = useAuth()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    // Hardcoded credentials
    if (email === "admin@trees.com" && password === "password") {
      login({ name: "Admin User", email, role: "admin" })
      router.push("/dashboard")
    } else if (email === "user@trees.com" && password === "password") {
      login({ name: "Regular User", email, role: "user" })
      router.push("/dashboard")
    } else {
      setError("Invalid credentials. Try admin@trees.com / password or user@trees.com / password")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-green-50 to-white p-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2 animate-fade-in">
            <div className="bg-primary/10 p-2 rounded-full">
              <Leaf className="h-10 w-10 text-primary" />
            </div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">Columbia Tree Observatory</h1>
          </div>
        </div>

        <Card className="animate-slide-up shadow-lg">
          <CardHeader>
            <CardTitle className="text-2xl">Login</CardTitle>
            <CardDescription>Enter your credentials to access the tree observatory</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="border-input"
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="text-sm font-medium">
                    Password
                  </label>
                  <Link href="#" className="text-xs text-primary hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="border-input"
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" className="w-full" size="lg">
                <LogIn className="mr-2 h-4 w-4" />
                Sign In
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <div className="flex items-center justify-between w-full">
              <Link href="/register" className="text-sm text-primary hover:underline">
                Don&apos;t have an account? Register
              </Link>
              <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
                Continue as guest
              </Link>
            </div>
            <div className="relative w-full">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">Demo Credentials</span>
              </div>
            </div>
            <div className="text-xs text-center text-muted-foreground">
              <p>Admin: admin@trees.com / password</p>
              <p>User: user@trees.com / password</p>
            </div>
          </CardFooter>
        </Card>

        <p className="text-center mt-8 text-sm text-muted-foreground animate-fade-in">
          © 2023 Columbia Tree Observatory. All rights reserved.
        </p>
      </div>
    </div>
  )
}
