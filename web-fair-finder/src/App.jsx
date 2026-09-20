import { Routes, Route } from 'react-router-dom';
import Header from './components/Header.jsx';
import HomePage from './pages/HomePage.jsx';
import FairDetailPage from './pages/FairDetailPage.jsx';

export default function App() {
  return (
    <div className="app">
      <Header />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/fair/:contentId" element={<FairDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
