import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthGate } from './AuthGate';

// Mock useAuth hook
const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

function renderWithRouter(initialPath = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="/login"
          element={<div data-testid="login-page">Login</div>}
        />
        <Route
          path="*"
          element={
            <AuthGate>
              <div data-testid="protected-content">Protected</div>
            </AuthGate>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AuthGate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading state while auth is checking', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: true });
    renderWithRouter();
    expect(screen.getByText(/checking authentication/i)).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    renderWithRouter();
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('redirects to /login when not authenticated', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    renderWithRouter('/dashboard');
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  it('stores intended path in sessionStorage before redirecting', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    renderWithRouter('/settings?tab=ai');
    expect(sessionStorage.getItem('solune-redirect-after-login')).toBe('/settings?tab=ai');
  });

  it('does not store root path before redirecting', () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, isLoading: false });
    renderWithRouter('/');
    expect(sessionStorage.getItem('solune-redirect-after-login')).toBeNull();
  });

  it('consumes stored redirect path after authentication', async () => {
    sessionStorage.setItem('solune-redirect-after-login', '/projects');
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });

    renderWithRouter('/');

    await waitFor(() => {
      expect(sessionStorage.getItem('solune-redirect-after-login')).toBeNull();
    });
  });
});
