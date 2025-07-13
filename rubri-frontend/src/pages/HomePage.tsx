import React from 'react';
import { Button } from '../components/ui';
import { 
  Brain, 
  Zap, 
  Target, 
  Clock, 
  Users, 
  CheckCircle,
  ArrowRight,
  FileText,
  Shield,
  Sparkles
} from 'lucide-react';

interface HomePageProps {
  onGetStarted: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onGetStarted }) => {
  const features = [
    {
      icon: Brain,
      title: 'AI-Powered Generation',
      description: 'Advanced multi-agent system creates deep, non-generic technical questions tailored to each candidate.'
    },
    {
      icon: Target,
      title: 'Precision Targeting',
      description: 'Questions specifically designed based on candidate experience and job requirements analysis.'
    },
    {
      icon: Clock,
      title: 'Time Efficient',
      description: 'Generate comprehensive interview plans in minutes, not hours of manual preparation.'
    },
    {
      icon: Users,
      title: 'Interviewer Guidance',
      description: 'Complete evaluation criteria, red flags, and follow-up questions for consistent assessment.'
    },
    {
      icon: Shield,
      title: 'Quality Assured',
      description: 'Built-in question evaluation ensures relevance, appropriate difficulty, and technical depth.'
    },
    {
      icon: FileText,
      title: 'Comprehensive Reports',
      description: 'Detailed interview plans with structured sections, timing, and candidate insights.'
    }
  ];

  const steps = [
    {
      step: 1,
      title: 'Upload Documents',
      description: 'Upload job description and/or resume files, or paste text directly.',
      icon: FileText
    },
    {
      step: 2,
      title: 'AI Analysis',
      description: 'Our 5-agent system analyzes skills, generates questions, and creates guidance.',
      icon: Brain
    },
    {
      step: 3,
      title: 'Get Results',
      description: 'Receive comprehensive interview plan with tailored questions and evaluation criteria.',
      icon: CheckCircle
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background-muted to-surface-100">
      {/* Hero Section */}
      <section className="relative px-4 pt-16 pb-24 sm:px-6 lg:px-8 hero-gradient">
        <div className="max-w-4xl mx-auto text-center">
          <div className="mb-8">
            <div className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium mb-4 shiny-badge glow-badge">
              <Sparkles className="h-4 w-4 mr-2" />
              AI-Powered Interview Plan Generation
            </div>
            <div className="text-green-500 text-sm font-medium mb-6 relative overflow-hidden">
              <span className="relative z-10 bg-gradient-to-r from-green-400 via-green-300 to-green-500 bg-clip-text text-transparent animate-shimmer-green">
                100% FREE - No Credit Card Required
              </span>
            </div>
          </div>
          
          <h1 className="text-4xl md:text-6xl font-bold text-foreground mb-6">
            Generate Perfect{' '}
            <span className="gradient-text shimmer-text">Interview</span>
            <br />
            <span className="gradient-text shimmer-text">Plan</span>{' '}
            in Minutes
          </h1>
          
          <p className="text-xl text-foreground-muted mb-8 max-w-3xl mx-auto leading-relaxed">
            Transform your hiring process for FREE with AI-generated, comprehensive interview questions 
            tailored to specific candidates and roles. Get deep technical questions, 
            evaluation criteria, and interviewer guidance instantly.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button 
              size="xl" 
              onClick={onGetStarted}
              leftIcon={Zap}
              className="shadow-primary hover:shadow-lg"
            >
              Generate Free Plan Now
            </Button>
            
            <Button 
              variant="outline" 
              size="xl"
              leftIcon={FileText}
              className="hover:shadow-md"
            >
              View Sample Plan
            </Button>
          </div>
          
          <div className="mt-12 flex items-center justify-center space-x-8 text-sm text-foreground-subtle">
            <div className="flex items-center">
              <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
              100% Free
            </div>
            <div className="flex items-center">
              <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
              AI Agent Powered
            </div>
            <div className="flex items-center">
              <CheckCircle className="h-4 w-4 text-green-400 mr-2" />
              Instant results
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-background-muted">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Why Choose Interview Valley?
            </h2>
            <p className="text-xl text-foreground-muted max-w-3xl mx-auto">
              Our advanced AI system goes beyond generic questions to create 
              sophisticated, tailored interview assessments.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} className="relative group">
                  <div className="bg-background p-8 rounded-xl shadow-soft border border-border hover:shadow-medium transition-all duration-300 group-hover:-translate-y-1">
                    <div className="bg-primary-500/20 p-3 rounded-lg w-fit mb-6">
                      <Icon className="h-6 w-6 text-primary-400" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-4">
                      {feature.title}
                    </h3>
                    <p className="text-foreground-muted leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              How It Works
            </h2>
            <p className="text-xl text-foreground-muted max-w-3xl mx-auto">
              Three simple steps to generate comprehensive interview questions 
              with our advanced AI system.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={index} className="relative">
                  <div className="text-center">
                    <div className="bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center text-xl font-bold mb-6 mx-auto">
                      {step.step}
                    </div>
                    <Icon className="h-12 w-12 text-primary-400 mx-auto mb-6" />
                    <h3 className="text-xl font-semibold text-foreground mb-4">
                      {step.title}
                    </h3>
                    <p className="text-foreground-muted leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                  
                  {index < steps.length - 1 && (
                    <div className="hidden md:block absolute top-16 left-full w-full">
                      <ArrowRight className="h-6 w-6 text-foreground-subtle mx-auto" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          
          <div className="text-center mt-12">
            <Button 
              size="lg" 
              onClick={onGetStarted}
              rightIcon={ArrowRight}
              className="shadow-medium hover:shadow-lg"
            >
              Try It Now
            </Button>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-background">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <div className="mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-xl text-foreground-muted max-w-2xl mx-auto">
              Professional interview plans at no cost. Start immediately and create unlimited interview assessments.
            </p>
          </div>
          
          <div className="max-w-md mx-auto">
            <div className="relative bg-surface-100 rounded-2xl border border-border p-8 shadow-medium hover:shadow-lg transition-all duration-300">
              {/* Free Badge */}
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <div className="bg-green-500 text-white px-4 py-2 rounded-full text-sm font-medium">
                  Free
                </div>
              </div>
              
              {/* Price */}
              <div className="mb-6 mt-4">
                <div className="flex items-baseline justify-center">
                  <span className="text-6xl font-bold text-foreground">$0</span>
                  <span className="text-xl text-foreground-muted ml-2">/month</span>
                </div>
                <p className="text-foreground-muted mt-2">No credit card required</p>
              </div>
              
              {/* Features */}
              <div className="space-y-4 mb-8">
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  <span className="text-foreground">Unlimited interview plans</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  <span className="text-foreground">AI-powered question generation</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  <span className="text-foreground">Professional report formats</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  <span className="text-foreground">All file formats supported</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  <span className="text-foreground">Instant results</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-400 mr-3" />
                  <span className="text-foreground">Email support</span>
                </div>
              </div>
              
              {/* CTA Button */}
              <Button 
                size="lg" 
                onClick={onGetStarted}
                className="w-full shadow-lg hover:shadow-xl"
              >
                Get Started Free
              </Button>
              
              <p className="text-foreground-subtle text-sm mt-4">
                No hidden fees • No trial limits • No strings attached
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-background-muted border-t border-border">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-6">
            Ready to Transform Your Interviews?
          </h2>
          <p className="text-xl text-foreground-muted mb-8 max-w-2xl mx-auto">
            Join thousands of hiring managers who use Interview Valley to create 
            better interviews and make smarter hiring decisions.
          </p>
          
          <Button 
            size="xl" 
            onClick={onGetStarted}
            leftIcon={Brain}
            className="shadow-lg hover:shadow-xl"
          >
            Generate Your First Report
          </Button>
          
          <p className="text-foreground-subtle text-sm mt-6">
            No credit card required • Free to use • Instant results
          </p>
        </div>
      </section>
    </div>
  );
};