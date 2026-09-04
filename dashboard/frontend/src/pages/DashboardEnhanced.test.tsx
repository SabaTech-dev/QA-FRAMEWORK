import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "react-query";
import type { AxiosResponse } from "axios";
import { MemoryRouter, useLocation } from "react-router-dom";
import DashboardEnhanced from "./DashboardEnhanced";
import { dashboardAPI } from "../api/client";
import { useRealTimeUpdates } from "../hooks/useRealTimeUpdates";

vi.mock("../api/client", () => ({
  dashboardAPI: {
    getStats: vi.fn(),
    getTrends: vi.fn(),
    getRecentExecutions: vi.fn(),
  },
}));

vi.mock("../hooks/useRealTimeUpdates", () => ({
  useRealTimeUpdates: vi.fn(),
}));

// chart.js renders on <canvas>, which jsdom does not provide; stub the
// react-chartjs-2 wrappers so the surrounding layout stays under test.
vi.mock("react-chartjs-2", () => ({
  Line: () => null,
  Bar: () => null,
  Doughnut: () => null,
}));

const mockGetStats = vi.mocked(dashboardAPI.getStats);
const mockGetTrends = vi.mocked(dashboardAPI.getTrends);
const mockGetRecent = vi.mocked(dashboardAPI.getRecentExecutions);
const mockToggleLive = vi.fn();
const mockUseRealTimeUpdates = vi.mocked(useRealTimeUpdates);

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

const renderDashboard = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <LocationProbe />
        <DashboardEnhanced />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const seedResolvedData = () => {
  mockGetStats.mockResolvedValue({
    data: {
      total_executions: 42,
      total_test_suites: 7,
      success_rate: 92,
      flaky_tests: 3,
    },
  } as any);
  mockGetTrends.mockResolvedValue({
    data: [
      { date: "2026-09-01", total: 10, passed: 8, failed: 2 },
      { date: "2026-09-02", total: 12, passed: 11, failed: 1 },
    ],
  } as any);
  mockGetRecent.mockResolvedValue({
    data: [
      {
        id: 1,
        suite_name: "Smoke Suite",
        environment: "staging",
        started_at: "2026-09-03 10:00",
        passed: 5,
        total_tests: 5,
        status: "completed",
      },
      {
        id: 2,
        suite_name: "Regression Pack",
        environment: "prod",
        started_at: "2026-09-03 11:00",
        passed: 3,
        total_tests: 4,
        status: "running",
      },
    ],
  } as any);
};

describe("DashboardEnhanced", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    seedResolvedData();
    mockUseRealTimeUpdates.mockReturnValue({
      isLive: true,
      lastUpdate: new Date("2026-09-04T08:00:00"),
      toggleLive: mockToggleLive,
    } as any);
  });

  it("renders without crash and shows the page heading", async () => {
    renderDashboard();

    expect(
      await screen.findByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it("shows a loading spinner while dashboard queries are pending", () => {
    mockGetStats.mockImplementation(() => new Promise<AxiosResponse>(() => {}));
    mockGetTrends.mockImplementation(() => new Promise<AxiosResponse>(() => {}));
    mockGetRecent.mockImplementation(() => new Promise<AxiosResponse>(() => {}));

    renderDashboard();

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("renders the AI disclosure banner required by EU AI Act Art. 50(1)", async () => {
    renderDashboard();

    await screen.findByRole("heading", { name: "Dashboard" });
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders stat cards with the values returned by the API", async () => {
    renderDashboard();

    expect(await screen.findByText("Total Executions")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Test Suites")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("Success Rate")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("renders chart section headers for trends and distribution", async () => {
    renderDashboard();

    expect(
      await screen.findByText("Execution Trends (Last 30 Days)"),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Types Distribution")).toBeInTheDocument();
  });

  it("renders recent executions with pass ratio and status chips", async () => {
    renderDashboard();

    expect(await screen.findByText("Smoke Suite")).toBeInTheDocument();
    expect(screen.getByText("5/5 passed")).toBeInTheDocument();
    expect(screen.getAllByText("completed")).toHaveLength(1);

    expect(screen.getByText("Regression Pack")).toBeInTheDocument();
    expect(screen.getByText("3/4 passed")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("refetches recent executions when Refresh is clicked", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText("Smoke Suite");
    expect(mockGetRecent).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => expect(mockGetRecent).toHaveBeenCalledTimes(2));
  });

  it("shows the live indicator and toggles polling on click", async () => {
    const user = userEvent.setup();
    renderDashboard();

    const liveChip = await screen.findByText("Live");
    await user.click(liveChip);

    expect(mockToggleLive).toHaveBeenCalledTimes(1);
  });

  it("navigates from quick action buttons", async () => {
    const user = userEvent.setup();
    renderDashboard();

    await screen.findByText("Smoke Suite");

    await user.click(screen.getByRole("button", { name: /new test suite/i }));
    expect(screen.getByTestId("location")).toHaveTextContent("/suites");

    await user.click(screen.getByRole("button", { name: /run tests/i }));
    expect(screen.getByTestId("location")).toHaveTextContent("/executions");
  });
});
