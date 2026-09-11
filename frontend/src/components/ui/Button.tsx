import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  block?: boolean;
}

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  block,
  className,
  children,
  ...props
}) => {
  const baseClasses = `
    btn
    focus-visible:outline-none
    focus-visible:ring-2
    focus-visible:ring-primary
    focus-visible:ring-offset-2
    disabled:opacity-50
    disabled:cursor-not-allowed
    transition-all
  `;

  const variantClasses = {
    primary: 'btn-primary hover:bg-primary-dark active:bg-primary-dark',
    secondary: 'btn-secondary hover:bg-tertiary active:bg-tertiary',
    outline: 'btn-outline hover:bg-primary hover:text-white active:bg-primary active:text-white'
  };

  const sizeClasses = {
    sm: 'px-3 py-1 text-sm',
    md: 'px-4 py-2',
    lg: 'px-5 py-3 text-lg'
  };

  const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${block ? 'w-full' : ''} ${className ?? ''}`;

  return (
    <button className={classes.trim()} {...props}>
      {children}
    </button>
  );
};

export default Button;