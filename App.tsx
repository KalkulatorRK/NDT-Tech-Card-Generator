
import React, { useState, useCallback } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import HomePage from './components/pages/HomePage';
import TechCardFormPage from './components/pages/TechCardFormPage';
import QualityAssessmentPage from './components/pages/QualityAssessmentPage';
import DashboardPage from './components/pages/DashboardPage';
import { Page } from './types';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<Page>(Page.Home);

  const navigate = useCallback((page: Page) => {
    setCurrentPage(page);
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case Page.Home:
        return <HomePage navigate={navigate} />;
      case Page.CreateTechCard:
        return <TechCardFormPage />;
      case Page.QualityAssessment:
        return <QualityAssessmentPage />;
      case Page.Dashboard:
        return <DashboardPage />;
      default:
        return <HomePage navigate={navigate} />;
    }
  };

  return (
    <div className="flex flex-col min-h-screen font-sans text-slate-800">
      <Header navigate={navigate} currentPage={currentPage} />
      <main className="flex-grow container mx-auto px-4 py-8">
        {renderPage()}
      </main>
      <Footer />
    </div>
  );
};

export default App;
