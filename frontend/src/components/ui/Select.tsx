import React from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options: Array<{ value: string | number; label: string }>;
}

const Select: React.FC<SelectProps> = ({
  label,
  error,
  helperText,
  options,
  className,
  ...props
}) => {
  const hasError = !!error;
  const selectClasses = `
    select
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
        <select
          className={ `${selectClasses} pl-10 pr-10 ${hasError ? 'border-red-500' : ''} ${className ?? ''}` }
          {...props}
        >
          <option value="">Select an option</option>
          {options.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="text-sm text-red-500 mt-1">{error}</p>}
      {!error && helperText && <p className="text-sm text-gray-500 mt-1">{helperText}</p>}
    </div>
  );
};

export default Select;