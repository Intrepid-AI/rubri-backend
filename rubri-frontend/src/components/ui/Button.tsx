import React, { forwardRef } from 'react'
import { Loader2, type LucideIcon } from 'lucide-react'
import { motion, type MotionProps } from 'framer-motion'
import { cn } from '../../lib/utils'
import { buttonVariants, type ButtonVariants } from '../../lib/variants'

interface ButtonProps 
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onDrag'>,
          ButtonVariants {
  /**
   * The content of the button
   */
  children: React.ReactNode
  /**
   * Whether the button is in a loading state
   */
  loading?: boolean
  /**
   * Icon to display before the button text
   */
  leftIcon?: LucideIcon
  /**
   * Icon to display after the button text
   */
  rightIcon?: LucideIcon
  /**
   * Whether to show only the icon (for icon buttons)
   */
  iconOnly?: boolean
  /**
   * Animation props from Framer Motion
   */
  motionProps?: MotionProps
  /**
   * Tooltip text for accessibility
   */
  tooltip?: string
}

/**
 * Professional Button component with enterprise-grade styling and functionality
 * 
 * Features:
 * - Multiple variants (primary, secondary, outline, ghost, destructive, success, warning, link)
 * - Different sizes (sm, md, lg, xl, icon)
 * - Loading states with spinner
 * - Icon support (left, right, icon-only)
 * - Animations with Framer Motion
 * - Full accessibility support
 * - TypeScript with proper variant types
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    variant = 'default',
    size = 'default',
    loading = false,
    disabled,
    className,
    children,
    leftIcon: LeftIcon,
    rightIcon: RightIcon,
    iconOnly = false,
    motionProps,
    tooltip,
    type = 'button',
    ...props
  }, ref) => {
    const isDisabled = disabled || loading
    
    // Motion variants for animations
    const buttonMotion = {
      whileTap: { scale: 0.98 },
      whileHover: { scale: 1.02 },
      transition: { type: "spring", stiffness: 400, damping: 17 },
      ...motionProps
    }
    
    // Icon size based on button size
    const iconSize = {
      sm: 14,
      default: 16,
      md: 16,
      lg: 18,
      xl: 20,
      icon: 16,
    }[size || 'default']
    
    const buttonContent = (
      <>
        {/* Loading spinner */}
        {loading && (
          <Loader2 
            size={iconSize} 
            className="animate-spin" 
            aria-hidden="true"
          />
        )}
        
        {/* Left icon */}
        {!loading && LeftIcon && (
          <LeftIcon 
            size={iconSize} 
            className={cn(
              'shrink-0',
              !iconOnly && children && 'mr-1'
            )}
            aria-hidden="true"
          />
        )}
        
        {/* Button text */}
        {!iconOnly && children && (
          <span className="truncate">
            {children}
          </span>
        )}
        
        {/* Icon-only content */}
        {iconOnly && !loading && !LeftIcon && children}
        
        {/* Right icon */}
        {!loading && RightIcon && !iconOnly && (
          <RightIcon 
            size={iconSize} 
            className={cn(
              'shrink-0',
              children && 'ml-1'
            )}
            aria-hidden="true"
          />
        )}
      </>
    )
    
    const buttonElement = (
      <motion.button
        ref={ref}
        type={type}
        className={cn(
          buttonVariants({ variant, size }),
          iconOnly && 'aspect-square',
          loading && 'opacity-50 cursor-not-allowed',
          className
        )}
        disabled={isDisabled}
        aria-label={iconOnly ? (typeof children === 'string' ? children : tooltip) : undefined}
        title={tooltip}
        whileTap={buttonMotion.whileTap}
        whileHover={buttonMotion.whileHover}
        transition={buttonMotion.transition as any}
        {...props}
      >
        {buttonContent}
      </motion.button>
    )
    
    return buttonElement
  }
)

Button.displayName = 'Button'

/**
 * Button group component for related actions
 */
interface ButtonGroupProps {
  children: React.ReactNode
  className?: string
  orientation?: 'horizontal' | 'vertical'
  size?: ButtonVariants['size']
  variant?: ButtonVariants['variant']
}

export const ButtonGroup: React.FC<ButtonGroupProps> = ({
  children,
  className,
  orientation = 'horizontal',
  size,
  variant
}) => {
  return (
    <div
      className={cn(
        'inline-flex',
        orientation === 'horizontal' ? 'flex-row' : 'flex-col',
        orientation === 'horizontal' ? '[&>button]:rounded-none [&>button:first-child]:rounded-l-lg [&>button:last-child]:rounded-r-lg [&>button:not(:last-child)]:border-r-0' : '[&>button]:rounded-none [&>button:first-child]:rounded-t-lg [&>button:last-child]:rounded-b-lg [&>button:not(:last-child)]:border-b-0',
        className
      )}
      role="group"
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child) && child.type === Button) {
          return React.cloneElement(child as React.ReactElement<ButtonProps>, {
            size: size || (child as React.ReactElement<ButtonProps>).props.size,
            variant: variant || (child as React.ReactElement<ButtonProps>).props.variant,
          })
        }
        return child
      })}
    </div>
  )
}

/**
 * Icon Button component for icon-only buttons
 */
interface IconButtonProps extends Omit<ButtonProps, 'children' | 'iconOnly'> {
  icon: LucideIcon
  label: string
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon: Icon, label, size = 'md', ...props }, ref) => {
    return (
      <Button
        ref={ref}
        size={size === 'md' ? 'icon' : size}
        iconOnly
        tooltip={label}
        {...props}
      >
        <Icon size={16} />
        <span className="sr-only">{label}</span>
      </Button>
    )
  }
)

IconButton.displayName = 'IconButton'