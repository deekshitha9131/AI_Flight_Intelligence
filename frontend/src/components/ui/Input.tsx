import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}

const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  iconLeft,
  iconRight,
  className,
  ...props
}) => {
  const hasError = !!error;
  const inputClasses = `
    input
    hover:border-primary
    focus:border-primary
    focus:ring-2
    focus:ring-primary
    focus:ring-offset-0
    disabled:bg-tertiary
    disabled:cursor-not-allowed
  `;

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={props.id || undefined} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <div className="relative">
        {iconLeft && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 flex h-5 items-center text-gray-400 pointer-events-none">
            {iconLeft}
          </div>
        )}
        {iconRight && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex h-5 items-center text-gray-400 pointer-events-none">
            {iconRight}
          </div>
        )}
        <input
          className={ `${inputClasses} pl-10 pr-10 ${hasError ? 'border-red-500' : ''} ${className ?? ''}` }
          {...props}
        />
      </div>
      {error && <p className="text-sm text-red-500 mt-1">{error}</p>}
      {!error && helperText && <p className="text-sm text-gray-500 mt-1">{helperText}</p>}
    </div>
  );
};

export default Input;