"use client"

import type React from "react"

import { useState } from "react"
import DashboardLayout from "@/components/dashboard-layout"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/context/auth-context"
import { Bell, Lock, User, Globe, Shield, Eye, EyeOff } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export default function SettingsPage() {
  const { user } = useAuth()
  const [showPassword, setShowPassword] = useState(false)
  const [settingsTab, setSettingsTab] = useState("account")

  const [formState, setFormState] = useState({
    name: user?.name || "",
    email: user?.email || "",
    password: "••••••••",
    notifications: {
      email: true,
      push: true,
      sms: false,
      weeklyReport: true,
      criticalAlerts: true,
    },
    preferences: {
      language: "english",
      theme: "system",
      mapStyle: "standard",
      dataRefreshRate: "hourly",
    },
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormState({
      ...formState,
      [name]: value,
    })
  }

  const handleSwitchChange = (field: string, checked: boolean) => {
    setFormState({
      ...formState,
      notifications: {
        ...formState.notifications,
        [field]: checked,
      },
    })
  }

  const handleSelectChange = (field: string, value: string) => {
    setFormState({
      ...formState,
      preferences: {
        ...formState.preferences,
        [field]: value,
      },
    })
  }

  const handleSaveSettings = () => {
    // Simulate saving settings
    alert("Settings saved successfully!")
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 animate-fade-in">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Settings</h1>
          <p className="mt-2 text-muted-foreground">Manage your account settings and preferences</p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="lg:col-span-1">
            <Tabs
              defaultValue="account"
              value={settingsTab}
              onValueChange={setSettingsTab}
              orientation="vertical"
              className="w-full"
            >
              <TabsList className="flex flex-col h-auto w-full bg-transparent space-y-1">
                <TabsTrigger value="account" className="justify-start w-full px-3 py-2 text-left">
                  <User className="mr-2 h-4 w-4" />
                  Account
                </TabsTrigger>
                <TabsTrigger value="notifications" className="justify-start w-full px-3 py-2 text-left">
                  <Bell className="mr-2 h-4 w-4" />
                  Notifications
                </TabsTrigger>
                <TabsTrigger value="security" className="justify-start w-full px-3 py-2 text-left">
                  <Lock className="mr-2 h-4 w-4" />
                  Security
                </TabsTrigger>
                <TabsTrigger value="preferences" className="justify-start w-full px-3 py-2 text-left">
                  <Globe className="mr-2 h-4 w-4" />
                  Preferences
                </TabsTrigger>
                <TabsTrigger value="permissions" className="justify-start w-full px-3 py-2 text-left">
                  <Shield className="mr-2 h-4 w-4" />
                  Permissions
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          <div className="lg:col-span-3">
            <Tabs value={settingsTab} className="w-full">
              <TabsContent value="account" className="mt-0">
                <Card>
                  <CardHeader>
                    <CardTitle>Account Information</CardTitle>
                    <CardDescription>Update your account details and personal information</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Full Name</Label>
                      <Input id="name" name="name" value={formState.name} onChange={handleInputChange} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="email">Email Address</Label>
                      <Input
                        id="email"
                        name="email"
                        type="email"
                        value={formState.email}
                        onChange={handleInputChange}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="role">Role</Label>
                      <Input id="role" value={user?.role || "Guest"} disabled />
                      <p className="text-xs text-muted-foreground">
                        Your role determines your permissions within the system
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bio">Bio</Label>
                      <Textarea id="bio" name="bio" placeholder="Tell us about yourself" className="min-h-[100px]" />
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <Button variant="outline">Cancel</Button>
                    <Button onClick={handleSaveSettings}>Save Changes</Button>
                  </CardFooter>
                </Card>
              </TabsContent>

              <TabsContent value="notifications" className="mt-0">
                <Card>
                  <CardHeader>
                    <CardTitle>Notification Settings</CardTitle>
                    <CardDescription>Configure how you receive notifications and alerts</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label htmlFor="email-notifications">Email Notifications</Label>
                          <p className="text-sm text-muted-foreground">Receive notifications via email</p>
                        </div>
                        <Switch
                          id="email-notifications"
                          checked={formState.notifications.email}
                          onCheckedChange={(checked) => handleSwitchChange("email", checked)}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label htmlFor="push-notifications">Push Notifications</Label>
                          <p className="text-sm text-muted-foreground">Receive notifications on your device</p>
                        </div>
                        <Switch
                          id="push-notifications"
                          checked={formState.notifications.push}
                          onCheckedChange={(checked) => handleSwitchChange("push", checked)}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label htmlFor="sms-notifications">SMS Notifications</Label>
                          <p className="text-sm text-muted-foreground">Receive notifications via text message</p>
                        </div>
                        <Switch
                          id="sms-notifications"
                          checked={formState.notifications.sms}
                          onCheckedChange={(checked) => handleSwitchChange("sms", checked)}
                        />
                      </div>
                    </div>

                    <div className="pt-4 border-t">
                      <h3 className="mb-4 text-sm font-medium">Notification Types</h3>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label htmlFor="weekly-report">Weekly Reports</Label>
                            <p className="text-sm text-muted-foreground">Receive weekly summary reports</p>
                          </div>
                          <Switch
                            id="weekly-report"
                            checked={formState.notifications.weeklyReport}
                            onCheckedChange={(checked) => handleSwitchChange("weeklyReport", checked)}
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label htmlFor="critical-alerts">Critical Alerts</Label>
                            <p className="text-sm text-muted-foreground">
                              Receive alerts for critical tree health issues
                            </p>
                          </div>
                          <Switch
                            id="critical-alerts"
                            checked={formState.notifications.criticalAlerts}
                            onCheckedChange={(checked) => handleSwitchChange("criticalAlerts", checked)}
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <Button variant="outline">Cancel</Button>
                    <Button onClick={handleSaveSettings}>Save Changes</Button>
                  </CardFooter>
                </Card>
              </TabsContent>

              <TabsContent value="security" className="mt-0">
                <Card>
                  <CardHeader>
                    <CardTitle>Security Settings</CardTitle>
                    <CardDescription>Manage your password and security preferences</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="current-password">Current Password</Label>
                      <div className="relative">
                        <Input
                          id="current-password"
                          type={showPassword ? "text" : "password"}
                          value={formState.password}
                          onChange={handleInputChange}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="absolute right-0 top-0 h-full px-3"
                          onClick={() => setShowPassword(!showPassword)}
                        >
                          {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          <span className="sr-only">Toggle password visibility</span>
                        </Button>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="new-password">New Password</Label>
                      <Input
                        id="new-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Enter new password"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirm-password">Confirm New Password</Label>
                      <Input
                        id="confirm-password"
                        type={showPassword ? "text" : "password"}
                        placeholder="Confirm new password"
                      />
                    </div>

                    <div className="pt-4 border-t">
                      <h3 className="mb-4 text-sm font-medium">Two-Factor Authentication</h3>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label htmlFor="two-factor">Enable Two-Factor Authentication</Label>
                          <p className="text-sm text-muted-foreground">
                            Add an extra layer of security to your account
                          </p>
                        </div>
                        <Switch id="two-factor" />
                      </div>
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <Button variant="outline">Cancel</Button>
                    <Button onClick={handleSaveSettings}>Save Changes</Button>
                  </CardFooter>
                </Card>
              </TabsContent>

              <TabsContent value="preferences" className="mt-0">
                <Card>
                  <CardHeader>
                    <CardTitle>Preferences</CardTitle>
                    <CardDescription>Customize your experience with the Tree Observatory</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="language">Language</Label>
                      <Select
                        value={formState.preferences.language}
                        onValueChange={(value) => handleSelectChange("language", value)}
                      >
                        <SelectTrigger id="language">
                          <SelectValue placeholder="Select language" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="english">English</SelectItem>
                          <SelectItem value="spanish">Spanish</SelectItem>
                          <SelectItem value="french">French</SelectItem>
                          <SelectItem value="portuguese">Portuguese</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="theme">Theme</Label>
                      <Select
                        value={formState.preferences.theme}
                        onValueChange={(value) => handleSelectChange("theme", value)}
                      >
                        <SelectTrigger id="theme">
                          <SelectValue placeholder="Select theme" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="light">Light</SelectItem>
                          <SelectItem value="dark">Dark</SelectItem>
                          <SelectItem value="system">System</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="map-style">Default Map Style</Label>
                      <Select
                        value={formState.preferences.mapStyle}
                        onValueChange={(value) => handleSelectChange("mapStyle", value)}
                      >
                        <SelectTrigger id="map-style">
                          <SelectValue placeholder="Select map style" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="standard">Standard</SelectItem>
                          <SelectItem value="satellite">Satellite</SelectItem>
                          <SelectItem value="terrain">Terrain</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="refresh-rate">Data Refresh Rate</Label>
                      <Select
                        value={formState.preferences.dataRefreshRate}
                        onValueChange={(value) => handleSelectChange("dataRefreshRate", value)}
                      >
                        <SelectTrigger id="refresh-rate">
                          <SelectValue placeholder="Select refresh rate" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="realtime">Real-time</SelectItem>
                          <SelectItem value="hourly">Hourly</SelectItem>
                          <SelectItem value="daily">Daily</SelectItem>
                          <SelectItem value="weekly">Weekly</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <Button variant="outline">Reset to Defaults</Button>
                    <Button onClick={handleSaveSettings}>Save Changes</Button>
                  </CardFooter>
                </Card>
              </TabsContent>

              <TabsContent value="permissions" className="mt-0">
                <Card>
                  <CardHeader>
                    <CardTitle>Permissions</CardTitle>
                    <CardDescription>Manage access permissions and roles</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>View Tree Data</Label>
                          <p className="text-sm text-muted-foreground">
                            Access to view tree information and statistics
                          </p>
                        </div>
                        <Switch defaultChecked disabled={user?.role !== "admin"} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Edit Tree Data</Label>
                          <p className="text-sm text-muted-foreground">Permission to edit tree information</p>
                        </div>
                        <Switch defaultChecked={user?.role === "admin"} disabled={user?.role !== "admin"} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Generate Reports</Label>
                          <p className="text-sm text-muted-foreground">Permission to generate and export reports</p>
                        </div>
                        <Switch defaultChecked disabled={user?.role !== "admin"} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label>Manage Users</Label>
                          <p className="text-sm text-muted-foreground">Permission to add, edit, and remove users</p>
                        </div>
                        <Switch defaultChecked={user?.role === "admin"} disabled={user?.role !== "admin"} />
                      </div>
                    </div>

                    {user?.role !== "admin" && (
                      <div className="mt-4 p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground">
                          Only administrators can modify permission settings. Please contact an administrator if you
                          need changes to your permissions.
                        </p>
                      </div>
                    )}
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <Button variant="outline" disabled={user?.role !== "admin"}>
                      Cancel
                    </Button>
                    <Button onClick={handleSaveSettings} disabled={user?.role !== "admin"}>
                      Save Changes
                    </Button>
                  </CardFooter>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
