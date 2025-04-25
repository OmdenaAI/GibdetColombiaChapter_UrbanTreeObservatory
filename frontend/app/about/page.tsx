"use client"

import { TreeDeciduous, Users, Globe, BarChart3, Shield } from "lucide-react"
import DashboardLayout from "@/components/dashboard-layout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export default function AboutPage() {
  return (
    <DashboardLayout>
      <div className="container mx-auto px-4 py-8 animate-fade-in">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-gray-800 mb-4">About Columbia Tree Observatory</h1>
            <p className="text-xl text-gray-600">
              Monitoring and preserving our urban forest ecosystem for future generations
            </p>
          </div>

          <div className="prose prose-lg max-w-none mb-12">
            <p>
              The Columbia Tree Observatory is a pioneering initiative dedicated to monitoring, analyzing, and
              preserving the urban forest ecosystem in Columbia. Our mission is to provide comprehensive data and
              insights about the city&apos;s trees, promoting environmental awareness and informed decision-making for
              sustainable urban forestry management.
            </p>
            <p>
              Established in 2020, our observatory combines cutting-edge technology with environmental science to track
              the health, growth, and environmental impact of trees across the city. We believe that a healthy urban
              forest is essential for improving air quality, reducing urban heat islands, enhancing biodiversity, and
              creating more livable spaces for all residents.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
            <Card className="animate-slide-up hover:shadow-md transition-shadow">
              <CardHeader className="bg-primary/5 dark:bg-primary/10">
                <CardTitle className="flex items-center gap-2">
                  <TreeDeciduous className="h-5 w-5 text-primary" />
                  Our Mission
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p>
                  To monitor, analyze, and preserve Columbia&apos;s urban forest ecosystem through data-driven insights
                  and community engagement, ensuring a sustainable and green future for all residents.
                </p>
              </CardContent>
            </Card>

            <Card className="animate-slide-up hover:shadow-md transition-shadow" style={{ animationDelay: "0.1s" }}>
              <CardHeader className="bg-primary/5 dark:bg-primary/10">
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5 text-primary" />
                  Our Vision
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <p>
                  A Columbia where urban forests thrive, biodiversity flourishes, and communities are connected through
                  a shared commitment to environmental stewardship and sustainable urban development.
                </p>
              </CardContent>
            </Card>
          </div>

          <h2 className="text-2xl font-bold text-gray-800 mb-6">What We Do</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <Card className="animate-slide-up">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  Data Collection & Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  We collect comprehensive data on tree species, health, growth, and environmental impact, providing
                  valuable insights for urban forestry management.
                </p>
              </CardContent>
            </Card>

            <Card className="animate-slide-up" style={{ animationDelay: "0.1s" }}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" />
                  Community Engagement
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  We engage with local communities, schools, and organizations to promote environmental awareness and
                  encourage participation in tree planting and conservation efforts.
                </p>
              </CardContent>
            </Card>

            <Card className="animate-slide-up" style={{ animationDelay: "0.2s" }}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  Advocacy & Policy
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  We advocate for policies that protect and enhance urban forests, working with local government and
                  stakeholders to develop sustainable urban forestry strategies.
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="bg-green-50 dark:bg-green-950/30 rounded-xl p-8 mb-12 animate-fade-in">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6">Our Impact</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <p className="text-4xl font-bold text-primary">5,000+</p>
                <p className="text-gray-600 dark:text-gray-300">Trees Monitored</p>
              </div>
              <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <p className="text-4xl font-bold text-primary">20+</p>
                <p className="text-gray-600 dark:text-gray-300">Species Tracked</p>
              </div>
              <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <p className="text-4xl font-bold text-primary">30%</p>
                <p className="text-gray-600 dark:text-gray-300">Canopy Coverage</p>
              </div>
              <div className="text-center p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                <p className="text-4xl font-bold text-primary">1,000+</p>
                <p className="text-gray-600 dark:text-gray-300">Community Members</p>
              </div>
            </div>
          </div>

          <div className="text-center mb-12 animate-fade-in">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">Join Our Efforts</h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6 max-w-2xl mx-auto">
              We welcome volunteers, researchers, and partners who share our passion for urban forestry and
              environmental conservation. Together, we can create a greener, healthier, and more sustainable Columbia.
            </p>
            <Button className="bg-primary text-white px-6 py-3 rounded-lg font-medium hover:bg-primary/90 transition-colors">
              Get Involved
            </Button>
          </div>

          <div className="border-t border-gray-200 pt-8 text-center animate-fade-in">
            <p className="text-gray-600">© 2023 Columbia Tree Observatory. All rights reserved.</p>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
