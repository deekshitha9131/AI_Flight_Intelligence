import React from 'react';

interface ErrorStateProps {
  title: string;
  description?: string;
  retryAction?: React.ReactNode;
  className?: string;
}

const ErrorState: React.FC<ErrorStateProps> = ({
  title,
  description,
  retryAction,
  className
}) => {
  return (
    <div className={`max-w-xl mx-auto text-center py-12 ${className ?? ''}`}>
      <div className="mx-auto mb-6 h-12 w-12 flex items-center justify-center rounded-full bg-red-50 text-red-500">
        {/* Simple error icon */}
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-6 w-6">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
      {description && <p className="text-gray-600 mb-6">{description}</p>}
      {retryAction && <div className="mt-4">{retryAction}</div>}
    </div>
  );
};

export default ErrorState;