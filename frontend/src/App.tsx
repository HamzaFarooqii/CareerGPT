import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, FileText, Briefcase, Target,
  User, LogIn, MessageSquare, Zap, ChevronRight,
  Activity
} from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';

const Scene3D      = lazy(() => import('./components/Scene3D'));
const Dashboard    = lazy(() => import('./pages/Dashboard'));
const Resumes      = lazy(() => import('./pages/Resumes'));
const Jobs         = lazy(() => import('./pages/Jobs'));
const Matches      = lazy(() => import('./pages/Matches'));
const Login        = lazy(() => import('./pages/Login'));
const Register     = lazy(() => import('./pages/Register'));
const Profile      = lazy(() => import('./pages/Profile'));
const CareerCoach  = lazy(() => import('./pages/CareerCoach'));
const ApplyAgent   = lazy(() => import('./pages/ApplyAgent'));

const NAV_MAIN = [
  { path: '/',          label: 'Dashboard',    icon: LayoutDashboard },
  { path: '/jobs',      label: 'Job Search',   icon: Briefcase },
  { path: '/resumes',   label: 'Resumes',      icon: FileText },
  { path: '/matches',   label: 'AI Matches',   icon: Target, badge: 'AI' },
];
const NAV_AI = [
  { path: '/coach',     label: 'Career Coach', icon: MessageSquare, badge: 'AI' },
  { path: '/apply',     label: 'Apply Agent',  icon: Zap, badge: 'AI' },
];

function Sidebar() {
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();
  const isAuth = location.pathname === '/login' || location.pathname === '/register';
  if (isAuth) return null;

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <img src="/logo.png" alt="CareerGPT" style={{ width: 38, height: 38, borderRadius: 10, flexShrink: 0 }} />
        <div>
          <h1>CareerGPT</h1>
          <span className="ver">v2.0 · GenAI</span>
        </div>
      </div>

      {/* Main nav */}
      <span className="nav-section-label">Platform</span>
      <ul className="nav-links">
        {NAV_MAIN.map(n => (
          <li key={n.path}>
            <NavLink
              to={n.path}
              end={n.path === '/'}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <n.icon size={16} />
              {n.label}
              {n.badge && <span className="badge">{n.badge}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* AI nav */}
      <span className="nav-section-label" style={{ marginTop: 20 }}>AI Features</span>
      <ul className="nav-links">
        {NAV_AI.map(n => (
          <li key={n.path}>
            <NavLink
              to={n.path}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <n.icon size={16} />
              {n.label}
              {n.badge && <span className="badge">{n.badge}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* Status */}
      <div style={{ marginTop: 'auto' }}>
        <div style={{
          padding: '12px 14px', borderRadius: 10,
          background: 'rgba(16,185,129,0.06)',
          border: '1px solid rgba(16,185,129,0.15)',
          marginBottom: 12,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="dot dot-green" />
            <span style={{ fontSize: '0.72rem', fontFamily: 'var(--mono)', color: 'var(--success)', fontWeight: 600 }}>
              AI Pipeline Active
            </span>
          </div>
          <div style={{ fontSize: '0.62rem', color: 'var(--text-3)', marginTop: 4, fontFamily: 'var(--mono)' }}>
            Groq LLM · ChromaDB
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
          {isAuthenticated ? (
            <NavLink
              to="/profile"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <div style={{
                width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.68rem', fontWeight: 800, color: 'white',
              }}>
                {user?.name?.[0]?.toUpperCase() || 'U'}
              </div>
              <div style={{ overflow: 'hidden', flex: 1 }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user?.name}
                </div>
                <div style={{ fontSize: '0.62rem', color: 'var(--text-3)' }}>View Profile</div>
              </div>
              <ChevronRight size={12} style={{ color: 'var(--text-3)' }} />
            </NavLink>
          ) : (
            <NavLink to="/login" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <LogIn size={16} /> Sign In
            </NavLink>
          )}
        </div>
      </div>
    </aside>
  );
}

function PageTransition({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
        style={{ height: '100%' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

function AppShell() {
  const location = useLocation();
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  return (
    <div className={isAuthPage ? '' : 'app-layout'}>
      {!isAuthPage && <Sidebar />}
      {!isAuthPage && (
        <Suspense fallback={null}>
          <Scene3D />
        </Suspense>
      )}
      <main className={isAuthPage ? '' : 'main-content'}>
        <Suspense fallback={
          <div className="loading-overlay">
            <div className="spinner" />
            <span>Loading...</span>
          </div>
        }>
          <PageTransition>
            <Routes>
              <Route path="/"         element={<Dashboard />} />
              <Route path="/resumes"  element={<Resumes />} />
              <Route path="/jobs"     element={<Jobs />} />
              <Route path="/matches"  element={<Matches />} />
              <Route path="/coach"    element={<CareerCoach />} />
              <Route path="/apply"    element={<ApplyAgent />} />
              <Route path="/profile"  element={<Profile />} />
              <Route path="/login"    element={<Login />} />
              <Route path="/register" element={<Register />} />
            </Routes>
          </PageTransition>
        </Suspense>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  );
}
