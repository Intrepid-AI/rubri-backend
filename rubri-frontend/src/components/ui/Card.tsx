import React, { forwardRef } from 'react'
import { motion, type MotionProps } from 'framer-motion'
import { type LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'
import { cardVariants, type CardVariants } from '../../lib/variants'

interface CardProps 
  extends Omit<React.HTMLAttributes<HTMLDivElement>, 'style'>,
          CardVariants {
  /**
   * The content of the card
   */
  children: React.ReactNode
  /**
   * Whether the card should be clickable/interactive
   */
  interactive?: boolean
  /**
   * Animation props from Framer Motion
   */
  motionProps?: MotionProps
  /**
   * Whether to add hover effects
   */
  hover?: boolean
}

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  /**
   * Title text for the card header
   */
  title?: string
  /**
   * Subtitle text for the card header
   */
  subtitle?: string
  /**
   * Icon to display in the header
   */
  icon?: LucideIcon
  /**
   * Action buttons/elements to display in the header
   */
  actions?: React.ReactNode
  /**
   * Whether to show a divider below the header
   */
  divider?: boolean
}

interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  /**
   * Whether to add extra padding
   */
  noPadding?: boolean
}

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  /**
   * Whether to show a divider above the footer
   */
  divider?: boolean
  /**
   * Justify content alignment
   */
  justify?: 'start' | 'center' | 'end' | 'between'
}

interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
  /**
   * The heading level (h1-h6)
   */
  level?: 1 | 2 | 3 | 4 | 5 | 6
}

interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

/**
 * Professional Card component with enterprise-grade styling and functionality
 * 
 * Features:
 * - Multiple variants (default, elevated, interactive, flat, outlined)
 * - Customizable padding levels
 * - Animation support with Framer Motion
 * - Structured header, content, and footer sections
 * - Icon and action support in headers
 * - Professional hover effects and interactions
 * - Full accessibility support
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({
    variant = 'default',
    padding = 'md',
    interactive = false,
    hover = false,
    className,
    children,
    motionProps,
    onClick,
    ...props
  }, ref) => {
    const isInteractive = interactive || !!onClick
    const shouldHover = hover || isInteractive
    
    const cardMotion = {
      whileHover: shouldHover ? { y: -2, transition: { duration: 0.2 } } : {},
      whileTap: isInteractive ? { scale: 0.98 } : {},
      ...motionProps
    }
    
    const Component = motionProps || shouldHover ? motion.div : 'div'
    
    return (
      <Component
        ref={ref}
        className={cn(
          cardVariants({ 
            variant: variant, 
            padding 
          }),
          isInteractive && 'cursor-pointer',
          className
        )}
        onClick={onClick}
        role={isInteractive ? 'button' : undefined}
        tabIndex={isInteractive ? 0 : undefined}
        onKeyDown={isInteractive ? (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onClick?.(e as any)
          }
        } : undefined}
        {...(shouldHover && cardMotion)}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Card.displayName = 'Card'

/**
 * Card Header component with title, subtitle, icon, and actions support
 */
export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({
    children,
    title,
    subtitle,
    icon: Icon,
    actions,
    divider = true,
    className,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-start justify-between p-6',
          divider && 'border-b border-gray-100',
          className
        )}
        {...props}
      >
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {Icon && (
            <div className="flex-shrink-0 mt-0.5">
              <Icon size={20} className="text-gray-600" />
            </div>
          )}
          
          <div className="min-w-0 flex-1">
            {title && (
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-gray-600 mt-1">
                {subtitle}
              </p>
            )}
            {children}
          </div>
        </div>
        
        {actions && (
          <div className="flex-shrink-0 ml-4">
            {actions}
          </div>
        )}
      </div>
    )
  }
)

CardHeader.displayName = 'CardHeader'

/**
 * Card Content component for the main content area
 */
export const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({
    children,
    noPadding = false,
    className,
    ...props
  }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          !noPadding && 'p-6',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

CardContent.displayName = 'CardContent'

/**
 * Card Footer component for actions and additional content
 */
export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({
    children,
    divider = true,
    justify = 'end',
    className,
    ...props
  }, ref) => {
    const justifyClasses = {
      start: 'justify-start',
      center: 'justify-center',
      end: 'justify-end',
      between: 'justify-between',
    }
    
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center gap-2 p-6',
          divider && 'border-t border-gray-100',
          justifyClasses[justify],
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

CardFooter.displayName = 'CardFooter'

/**
 * Card Title component for semantic heading structure
 */
export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({
    children,
    level = 3,
    className,
    ...props
  }, ref) => {
    const Component = `h${level}` as const
    
    return (
      <Component
        ref={ref}
        className={cn(
          'text-lg font-semibold text-gray-900 leading-tight',
          className
        )}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

CardTitle.displayName = 'CardTitle'

/**
 * Card Description component for descriptive text
 */
export const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({
    children,
    className,
    ...props
  }, ref) => {
    return (
      <p
        ref={ref}
        className={cn(
          'text-sm text-gray-600 leading-relaxed',
          className
        )}
        {...props}
      >
        {children}
      </p>
    )
  }
)

CardDescription.displayName = 'CardDescription'

/**
 * Specialized Card components for common use cases
 */

/**
 * Stat Card for displaying metrics and statistics
 */
interface StatCardProps extends Omit<CardProps, 'children'> {
  title: string
  value: string | number
  change?: {
    value: string | number
    trend: 'up' | 'down' | 'neutral'
  }
  icon?: LucideIcon
  description?: string
}

export const StatCard = forwardRef<HTMLDivElement, StatCardProps>(
  ({
    title,
    value,
    change,
    icon: Icon,
    description,
    className,
    ...props
  }, ref) => {
    const trendColors = {
      up: 'text-success-600',
      down: 'text-danger-600',
      neutral: 'text-gray-600',
    }
    
    return (
      <Card
        ref={ref}
        variant="elevated"
        className={cn('relative overflow-hidden', className)}
        {...props}
      >
        <CardContent>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-600 truncate">
                {title}
              </p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {value}
              </p>
              {description && (
                <p className="text-xs text-gray-500 mt-1">
                  {description}
                </p>
              )}
            </div>
            
            {Icon && (
              <div className="flex-shrink-0">
                <Icon size={24} className="text-gray-400" />
              </div>
            )}
          </div>
          
          {change && (
            <div className={cn(
              'flex items-center mt-3 text-sm font-medium',
              trendColors[change.trend]
            )}>
              <span>{change.value}</span>
              {change.trend !== 'neutral' && (
                <span className="ml-1">
                  {change.trend === 'up' ? '↗' : '↘'}
                </span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }
)

StatCard.displayName = 'StatCard'