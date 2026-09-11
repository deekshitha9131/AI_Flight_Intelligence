import React from 'react';

interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
  footer?: React.ReactNode;
  headerActions?: React.ReactNode;
}

const Card: React.FC<CardProps> = ({
  title,
  children,
  className,
  footer,
  headerActions
}) => {
  return (
    <div className={`card shadow-md ${className ?? ''}`}>
      {title || headerActions ? (
        <div className="card-header flex justify-between items-start py-4 px-6">
          <div>
            {title && <h3 className="text-lg font-semibold text-gray-800">{title}</h3>}
          </div>
          {headerActions}
        </div>
      ) : null}
      <div className="card-body px-6 py-5">{children}</div>
      {footer ? (
        <div className="card-footer px-6 py-4 text-right">{footer}</div>
      ) : null}
    </div>
  );
};

export default Card;