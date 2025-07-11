import React, { useState } from 'react';
import { Header, Footer } from './components/layout';
import { HomePage, GeneratorPage } from './pages';
import { ThemeProvider } from './contexts/ThemeContext';

type AppState = 'home' | 'generator';

function App() {
  const [currentPage, setCurrentPage] = useState<AppState>('home');

  const handleNavigateToGenerator = () => {
    setCurrentPage('generator');
  };

  const handleNavigateToHome = () => {
    setCurrentPage('home');
  };

  return (
    <ThemeProvider>
      <div className="min-h-screen flex flex-col">
        <Header />
        
        <main className="flex-1">
          {currentPage === 'home' ? (
            <HomePage onGetStarted={handleNavigateToGenerator} />
          ) : (
            <GeneratorPage onBack={handleNavigateToHome} />
          )}
        </main>
        
        <Footer />
      </div>
    </ThemeProvider>
  );
}

export default App;
