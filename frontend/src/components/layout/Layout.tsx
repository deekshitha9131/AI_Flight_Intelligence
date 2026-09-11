import React from 'react';
import Navbar from '../Navbar';

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-main">{children}</main>
      <footer className="app-footer"><div className="footer-inner"><span>AI Flight Intelligence</span><span>Search smarter. Travel with confidence.</span></div></footer>
    </div>
  );
};

export default Layout;
