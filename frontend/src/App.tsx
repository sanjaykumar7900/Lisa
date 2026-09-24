import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { TestRunsPage } from './pages/TestRunsPage';
import { BugsPage } from './pages/BugsPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const handleSelectProject = (id: string) => {
    setSelectedProjectId(id);
    setActiveTab('project-detail');
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardPage onSelectProject={handleSelectProject} />;
      case 'projects':
        return <ProjectsPage onSelectProject={handleSelectProject} />;
      case 'project-detail':
        return selectedProjectId ? (
          <ProjectDetailPage projectId={selectedProjectId} onDeleted={() => { setSelectedProjectId(null); setActiveTab('projects'); }} />
        ) : (
          <ProjectsPage onSelectProject={handleSelectProject} />
        );
      case 'test-runs':
        return <TestRunsPage />;
      case 'bugs':
        return <BugsPage />;
      case 'reports':
        return <ReportsPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <DashboardPage onSelectProject={handleSelectProject} />;
    }
  };

  const getPageTitle = () => {
    switch (activeTab) {
      case 'dashboard':
        return 'Dashboard Overview';
      case 'projects':
        return 'Projects';
      case 'project-detail':
        return 'Project details';
      case 'test-runs':
        return 'Test runs';
      case 'bugs':
        return 'Issues found';
      case 'reports':
        return 'QA Reports';
      case 'settings':
        return 'Settings';
      default:
        return 'Dashboard';
    }
  };

  return (
    <div className="command-grid flex min-h-screen bg-[#05070B] text-slate-100">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title={getPageTitle()} />
        <main className="flex-1 p-5 md:p-8 overflow-y-auto">{renderContent()}</main>
      </div>
    </div>
  );
}

export default App;
