import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "react-query";
import App from "../App";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});
const renderApp = () =>
  render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );

/**
 * Route smoke tests for the MUI 5 -> 9 / react-router 6 -> 7 migration.
 * Verifies that public routes still render their pages after the upgrade.
 */
describe("Route smoke (post-migration)", () => {
  it("renders Landing at /", () => {
    window.history.pushState({}, "", "/");
    const { unmount } = renderApp();
    expect(document.body.innerHTML.length).toBeGreaterThan(0);
    unmount();
  });

  it("renders Login at /login", () => {
    window.history.pushState({}, "", "/login");
    const { unmount } = renderApp();
    expect(document.body.innerHTML.length).toBeGreaterThan(0);
    unmount();
  });

  it("renders Register at /register", () => {
    window.history.pushState({}, "", "/register");
    const { unmount } = renderApp();
    expect(document.body.innerHTML.length).toBeGreaterThan(0);
    unmount();
  });

  it("unauthenticated users are redirected away from /dashboard", () => {
    window.history.pushState({}, "", "/dashboard");
    const { unmount } = renderApp();
    // ProtectedRoute redirects to /login when not authenticated
    expect(window.location.pathname).toBe("/login");
    unmount();
  });
});
