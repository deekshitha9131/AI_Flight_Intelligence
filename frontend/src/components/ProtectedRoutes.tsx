import React from 'react';
import PrivateRoute from './PrivateRoute';
import Layout from './layout/Layout';

// This component wraps the PrivateRoute and adds a navbar and layout
const ProtectedRoutes: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <PrivateRoute>
      <Layout>
        {children}
      </Layout>
    </PrivateRoute>
  );
};

export default ProtectedRoutes;