import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches uncaught errors thrown during rendering anywhere in the tree below
 * it and shows a recoverable fallback instead of letting React unmount the
 * entire app to a blank page.
 *
 * Without this, a single bad API response shape reaching `.map()`/`.filter()`
 * in any page component blanks the WHOLE app, not just that page — this
 * happened for real when the Jobs page treated a non-array API response as
 * an array. An error boundary can't stop that kind of bug from existing, but
 * it stops it from taking down navigation, the sidebar, and every other page
 * along with it.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Uncaught render error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 14, height: '100%', minHeight: 300, padding: 32, textAlign: 'center',
        }}>
          <AlertTriangle size={40} style={{ color: 'var(--warning, #fbbf24)' }} />
          <div style={{ fontWeight: 700, fontSize: '1rem' }}>Something went wrong on this page</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-3, #888)', maxWidth: 420 }}>
            {this.state.error.message || 'An unexpected error occurred.'}
          </div>
          <button
            className="btn btn-primary"
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: 4 }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
