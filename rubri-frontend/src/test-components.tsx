import React from 'react'
import { 
  Button, 
  Card, 
  CardHeader, 
  CardContent, 
  CardFooter,
  Input,
  StatCard
} from './components/ui'
import { 
  Zap, 
  FileText, 
  Settings, 
  Heart,
  Star,
  TrendingUp
} from 'lucide-react'

/**
 * Test page to verify all our professional components are working
 * Visit this by temporarily updating App.tsx to render this component
 */
export const TestComponents: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Interview Valley Components
          </h1>
          <p className="text-xl text-gray-600">
            Testing our <span className="gradient-text">enterprise-grade</span> component library
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Your path to better Hires
          </p>
        </div>

        {/* Button Variants */}
        <Card>
          <CardHeader title="Button Variants" subtitle="Professional button components with animations" />
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Button variant="primary" leftIcon={Zap}>Primary</Button>
              <Button variant="secondary" leftIcon={FileText}>Secondary</Button>
              <Button variant="outline" leftIcon={Settings}>Outline</Button>
              <Button variant="ghost" leftIcon={Heart}>Ghost</Button>
              <Button variant="destructive">Destructive</Button>
              <Button variant="success" rightIcon={Star}>Success</Button>
              <Button variant="warning">Warning</Button>
              <Button variant="link">Link Button</Button>
            </div>
            
            <div className="mt-6 flex gap-4 items-center">
              <Button size="sm">Small</Button>
              <Button size="md">Medium</Button>
              <Button size="lg">Large</Button>
              <Button size="xl">Extra Large</Button>
              <Button loading>Loading</Button>
            </div>
          </CardContent>
        </Card>

        {/* Input Variants */}
        <Card>
          <CardHeader title="Input Components" subtitle="Professional form inputs with states" />
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input 
                label="Default Input" 
                placeholder="Enter text here..." 
              />
              <Input 
                label="With Icon" 
                placeholder="Search..." 
                leftIcon={FileText}
              />
              <Input 
                label="Error State" 
                placeholder="Invalid input" 
                error="This field is required"
              />
              <Input 
                label="Success State" 
                placeholder="Valid input" 
                success="Looks good!"
                value="Valid input"
              />
              <Input 
                label="Password" 
                type="password" 
                placeholder="Enter password" 
              />
              <Input 
                label="Clearable" 
                placeholder="Type to see clear button" 
                clearable
              />
            </div>
          </CardContent>
        </Card>

        {/* Card Variants */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card variant="default">
            <CardHeader title="Default Card" />
            <CardContent>
              <p>Standard card with soft shadow</p>
            </CardContent>
          </Card>
          
          <Card variant="elevated">
            <CardHeader title="Elevated Card" />
            <CardContent>
              <p>Card with medium shadow for emphasis</p>
            </CardContent>
          </Card>
          
          <Card variant="interactive" hover>
            <CardHeader title="Interactive Card" />
            <CardContent>
              <p>Hover me! Interactive with animations</p>
            </CardContent>
          </Card>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            title="Total Questions Generated"
            value="12,345"
            change={{ value: "+12%", trend: "up" }}
            icon={TrendingUp}
          />
          <StatCard
            title="Active Users"
            value="1,234"
            change={{ value: "+5%", trend: "up" }}
            icon={Star}
          />
          <StatCard
            title="Success Rate"
            value="94.5%"
            change={{ value: "-2%", trend: "down" }}
            icon={Heart}
          />
        </div>

        {/* Professional Layout */}
        <Card variant="elevated">
          <CardHeader 
            title="Professional Enterprise Layout" 
            subtitle="Demonstrating advanced card features"
            icon={Zap}
            actions={
              <div className="flex gap-2">
                <Button variant="outline" size="sm">Edit</Button>
                <Button size="sm">Save</Button>
              </div>
            }
          />
          <CardContent>
            <p className="text-gray-600 leading-relaxed">
              This demonstrates our professional card layout with header icons, 
              action buttons, proper typography, and consistent spacing. The design 
              follows enterprise UI patterns with accessibility support and smooth animations.
            </p>
          </CardContent>
          <CardFooter justify="between">
            <p className="text-sm text-gray-500">Last updated: Today</p>
            <Button variant="ghost" size="sm">View Details</Button>
          </CardFooter>
        </Card>

      </div>
    </div>
  )
}