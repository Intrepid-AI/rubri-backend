import React, { forwardRef, useState } from 'react'
import { Eye, EyeOff, Search, X, type LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'
import { inputVariants, type InputVariants } from '../../lib/variants'

interface InputProps 
  extends React.InputHTMLAttributes<HTMLInputElement>,
          InputVariants {
  /**
   * Label text for the input
   */
  label?: string
  /**
   * Error message to display
   */
  error?: string
  /**
   * Helper text to display below the input
   */
  helper?: string
  /**
   * Icon to display on the left side
   */
  leftIcon?: LucideIcon
  /**
   * Icon to display on the right side
   */
  rightIcon?: LucideIcon
  /**
   * Whether this is a required field
   */
  required?: boolean
  /**
   * Whether to show a clear button
   */
  clearable?: boolean
  /**
   * Callback when clear button is clicked
   */
  onClear?: () => void
  /**
   * Whether the input is loading
   */
  loading?: boolean
  /**
   * Success message to display
   */
  success?: string
  /**
   * Warning message to display
   */
  warning?: string
}

interface TextareaProps 
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement>,
          InputVariants {
  label?: string
  error?: string
  helper?: string
  required?: boolean
  loading?: boolean
  success?: string
  warning?: string
  /**
   * Whether to auto-resize based on content
   */
  autoResize?: boolean
}

interface FormFieldProps {
  children: React.ReactNode
  label?: string
  error?: string
  helper?: string
  success?: string
  warning?: string
  required?: boolean
  className?: string
}

/**
 * Professional Input component with enterprise-grade styling and functionality
 * 
 * Features:
 * - Multiple variants (default, error, success, warning)
 * - Different sizes (sm, md, lg)
 * - Icon support (left, right)
 * - Loading states
 * - Clear functionality
 * - Password visibility toggle
 * - Full accessibility support
 * - Floating label animation
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({
    variant = 'default',
    size = 'md',
    label,
    error,
    helper,
    success,
    warning,
    leftIcon: LeftIcon,
    rightIcon: RightIcon,
    required,
    clearable,
    onClear,
    loading,
    className,
    id,
    type = 'text',
    value,
    onChange,
    ...props
  }, ref) => {
    const [showPassword, setShowPassword] = useState(false)
    const [focused, setFocused] = useState(false)
    
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
    const hasValue = value !== undefined ? String(value).length > 0 : false
    const isPassword = type === 'password'
    const currentType = isPassword && showPassword ? 'text' : type
    
    // Determine variant based on state
    const currentVariant = error ? 'error' : success ? 'success' : warning ? 'warning' : variant
    
    // Calculate if we should show right icons
    const showClearButton = clearable && hasValue && !loading
    const showPasswordToggle = isPassword
    const showRightIcon = RightIcon && !showClearButton && !showPasswordToggle && !loading
    
    const handleClear = () => {
      onClear?.()
      if (onChange) {
        const event = {
          target: { value: '' }
        } as React.ChangeEvent<HTMLInputElement>
        onChange(event)
      }
    }
    
    return (
      <FormField
        label={label}
        error={error}
        helper={helper}
        success={success}
        warning={warning}
        required={required}
      >
        <div className="relative">
          {/* Left Icon */}
          {LeftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
              <LeftIcon size={16} />
            </div>
          )}
          
          {/* Input Field */}
          <input
            ref={ref}
            id={inputId}
            type={currentType}
            value={value}
            onChange={onChange}
            onFocus={(e) => {
              setFocused(true)
              props.onFocus?.(e)
            }}
            onBlur={(e) => {
              setFocused(false)
              props.onBlur?.(e)
            }}
            className={cn(
              inputVariants({ variant: currentVariant, size }),
              LeftIcon && 'pl-10',
              (showClearButton || showPasswordToggle || showRightIcon || loading) && 'pr-10',
              className
            )}
            {...props}
          />
          
          {/* Floating Label */}
          {label && (
            <label
              htmlFor={inputId}
              className={cn(
                'absolute left-3 transition-all duration-200 pointer-events-none select-none',
                LeftIcon && 'left-10',
                focused || hasValue
                  ? 'top-0 -translate-y-1/2 bg-white px-1 text-xs font-medium text-primary-600'
                  : 'top-1/2 -translate-y-1/2 text-sm text-gray-400'
              )}
            >
              {label}
              {required && <span className="text-red-500 ml-1">*</span>}
            </label>
          )}
          
          {/* Right Side Icons */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {/* Loading Spinner */}
            {loading && (
              <div className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-primary-600 rounded-full" />
            )}
            
            {/* Clear Button */}
            {showClearButton && (
              <button
                type="button"
                onClick={handleClear}
                className="text-gray-400 hover:text-gray-600 p-0.5 rounded transition-colors"
                tabIndex={-1}
              >
                <X size={14} />
              </button>
            )}
            
            {/* Password Toggle */}
            {showPasswordToggle && (
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-gray-400 hover:text-gray-600 p-0.5 rounded transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            )}
            
            {/* Right Icon */}
            {showRightIcon && <RightIcon size={16} className="text-gray-400" />}
          </div>
        </div>
      </FormField>
    )
  }
)

Input.displayName = 'Input'

/**
 * Search Input component with search-specific styling
 */
interface SearchInputProps extends Omit<InputProps, 'leftIcon' | 'type'> {
  onSearch?: (value: string) => void
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ onSearch, placeholder = 'Search...', ...props }, ref) => {
    return (
      <Input
        ref={ref}
        type="search"
        leftIcon={Search}
        placeholder={placeholder}
        clearable
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            onSearch?.(e.currentTarget.value)
          }
          props.onKeyDown?.(e)
        }}
        {...props}
      />
    )
  }
)

SearchInput.displayName = 'SearchInput'

/**
 * Professional Textarea component
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({
    variant = 'default',
    size = 'md',
    label,
    error,
    helper,
    success,
    warning,
    required,
    loading,
    autoResize = false,
    className,
    id,
    rows = 4,
    ...props
  }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
    const currentVariant = error ? 'error' : success ? 'success' : warning ? 'warning' : variant
    
    return (
      <FormField
        label={label}
        error={error}
        helper={helper}
        success={success}
        warning={warning}
        required={required}
      >
        <textarea
          ref={ref}
          id={inputId}
          rows={rows}
          className={cn(
            inputVariants({ variant: currentVariant, size }),
            'resize-vertical',
            autoResize && 'resize-none',
            className
          )}
          {...props}
        />
      </FormField>
    )
  }
)

Textarea.displayName = 'Textarea'

/**
 * Form Field wrapper component for consistent field styling
 */
export const FormField = forwardRef<HTMLDivElement, FormFieldProps>(
  ({
    children,
    label,
    error,
    helper,
    success,
    warning,
    required,
    className,
    ...props
  }, ref) => {
    const message = error || success || warning || helper
    const messageType = error ? 'error' : success ? 'success' : warning ? 'warning' : 'helper'
    
    const messageClasses = {
      error: 'text-red-600',
      success: 'text-green-600',
      warning: 'text-yellow-600',
      helper: 'text-gray-500',
    }
    
    return (
      <div ref={ref} className={cn('w-full space-y-2', className)} {...props}>
        {children}
        
        {message && (
          <p className={cn('text-sm', messageClasses[messageType])}>
            {message}
          </p>
        )}
      </div>
    )
  }
)

FormField.displayName = 'FormField'

/**
 * Form Label component for consistent labeling
 */
interface FormLabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  children: React.ReactNode
  required?: boolean
}

export const FormLabel = forwardRef<HTMLLabelElement, FormLabelProps>(
  ({ children, required, className, ...props }, ref) => {
    return (
      <label
        ref={ref}
        className={cn(
          'block text-sm font-medium text-gray-900 mb-2',
          className
        )}
        {...props}
      >
        {children}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
    )
  }
)

FormLabel.displayName = 'FormLabel'

/**
 * Form Error component for error messages
 */
interface FormErrorProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

export const FormError = forwardRef<HTMLParagraphElement, FormErrorProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={cn('text-sm text-red-600 font-medium', className)}
        {...props}
      >
        {children}
      </p>
    )
  }
)

FormError.displayName = 'FormError'