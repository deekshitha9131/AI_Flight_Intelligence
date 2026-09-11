import React from 'react';

interface BadgeProps {
  variant?: 'primary' | 'success' | 'warning' | 'error';
  className?: string;
  children: React.ReactNode;
}

const Badge: React.FC<BadgeProps> = ({
  variant = 'primary',
  className,
  children
}) => {
  const variantClasses = {
    primary: 'bg-primary-light text-primary-dark',
    success: 'bg-green-50 text-green-800',
    warning: 'bg-yellow-50 text-yellow-800',
    error: 'bg-red-50 text-red-800'
  };

  const classes = `badge inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full ${variantClasses[variant]} ${className ?? ''}`;

  return <span className={classes}>{children}</span>;
};

export default Badge;