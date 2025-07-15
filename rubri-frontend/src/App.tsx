import { useState, useEffect } from 'react';
import { Header, Footer } from './components/layout';
import { HomePage, GeneratorPage } from './pages';
import { ThemeProvider } from './contexts/ThemeContext';

type AppState = 'home' | 'generator';

function App() {
  const [currentPage, setCurrentPage] = useState<AppState>('home');

  // Listen for navigation events from OAuth callback
  useEffect(() => {
    const handleNavigateToGenerator = () => {
      setCurrentPage('generator');
    };

    window.addEventListener('navigate-to-generator', handleNavigateToGenerator);
    return () => {
      window.removeEventListener('navigate-to-generator', handleNavigateToGenerator);
    };
  }, []);

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
