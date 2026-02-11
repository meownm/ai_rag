import { Navigate, Route, Routes } from 'react-router-dom';
import { Shell } from './components/layout/Shell';
import { QueryPage } from './pages/QueryPage';
import { IngestionPage } from './pages/IngestionPage';
import { DiagnosticsPage } from './pages/DiagnosticsPage';

export function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/query" replace />} />
        <Route path="/query" element={<QueryPage />} />
        <Route path="/ingestion" element={<IngestionPage />} />
        <Route path="/diagnostics" element={<DiagnosticsPage />} />
      </Routes>
    </Shell>
  );
}
