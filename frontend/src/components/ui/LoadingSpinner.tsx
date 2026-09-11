import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className,
  label
}) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-8 w-8'
  };

  const classes = `animate-spin rounded-full border-2 border-transparent border-t-primary ${sizeClasses[size]} ${className ?? ''}`;

  return (
    <div className="flex items-center space-x-2">
      <div className={classes} aria-label="Loading"></div>
      {label && <span className="text-sm text-primary">{label}</span>}
    </div>
  );
};

export default LoadingSpinner;