import { Component, type ErrorInfo, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

type ErrorBoundaryProps = {
  children: ReactNode;
  fallback?: ReactNode;
  resetKey?: string;
};

type ErrorBoundaryState = {
  hasError: boolean;
  error: Error | null;
};

class ErrorBoundaryInner extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false, error: null });
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Unhandled UI error captured by ErrorBoundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <section className="page-section">
            <div className="message error">
              Something went wrong on this view. Please try navigating to another page or refreshing.
            </div>
          </section>
        )
      );
    }

    return this.props.children;
  }
}

export function ErrorBoundary(props: { children: ReactNode; fallback?: ReactNode }) {
  const location = useLocation();
  return (
    <ErrorBoundaryInner resetKey={location.pathname} fallback={props.fallback}>
      {props.children}
    </ErrorBoundaryInner>
  );
}
