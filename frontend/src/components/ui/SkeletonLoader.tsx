import React from 'react';

interface SkeletonLoaderProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  rounded?: boolean;
}

const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  width = '100%',
  height = '1rem',
  className,
  rounded = false
}) => {
  const classes = `
    animate-pulse
    bg-gray-100
    ${typeof width === 'number' ? `w-[${width}px]` : `w-${width}`}
    ${typeof height === 'number' ? `h-[${height}px]` : `h-${height}`}
    ${rounded ? 'rounded' : ''}
    ${className ?? ''}
  `;

  return <div className={classes} aria-label="Loading skeleton"></div>;
};

export default SkeletonLoader;