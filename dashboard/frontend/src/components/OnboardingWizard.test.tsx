import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "react-query";
import type { AxiosResponse } from "axios";
import { MemoryRouter } from "react-router-dom";
import OnboardingWizard from "./OnboardingWizard";
import { onboardingAPI, suitesAPI } from "../api/client";
import toast from "react-hot-toast";

// localStorage is not populated as a global by this vitest+jsdom combo, so
// the real authStore (zustand persist) cannot run in tests; mock the module.
const { mockSetNeedsOnboarding } = vi.hoisted(() => ({
  mockSetNeedsOnboarding: vi.fn(),
}));

vi.mock("../stores/authStore", () => ({
  default: () => ({ setNeedsOnboarding: mockSetNeedsOnboarding }),
}));

vi.mock("../api/client", () => ({
  onboardingAPI: {
    getState: vi.fn(),
    updateStep: vi.fn(),
    complete: vi.fn(),
    skip: vi.fn(),
  },
  suitesAPI: {
    create: vi.fn(),
  },
  executionsAPI: {},
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockGetState = vi.mocked(onboardingAPI.getState);
const mockUpdateStep = vi.mocked(onboardingAPI.updateStep);
const mockComplete = vi.mocked(onboardingAPI.complete);
const mockSkip = vi.mocked(onboardingAPI.skip);
const mockCreateSuite = vi.mocked(suitesAPI.create);

const renderWizard = (onComplete: () => void = vi.fn()) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OnboardingWizard onComplete={onComplete} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const pendingState = () => {
  mockGetState.mockImplementation(() => new Promise<AxiosResponse>(() => {}));
};

const freshState = () => {
  mockGetState.mockResolvedValue({
    data: { completed: false, current_step: 0, steps: {} },
  } as any);
};

describe("OnboardingWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    freshState();
    mockUpdateStep.mockResolvedValue({ data: {} } as any);
    mockComplete.mockResolvedValue({ data: {} } as any);
    mockSkip.mockResolvedValue({ data: {} } as any);
    mockCreateSuite.mockResolvedValue({ data: {} } as any);
  });

  it("renders without crash and shows all five steps after loading", async () => {
    renderWizard();

    expect(
      await screen.findByText(/Welcome to QA-FRAMEWORK/),
    ).toBeInTheDocument();
    // step labels live in the Stepper; "Notifications" also appears in the
    // welcome step content, so scope the query to the StepLabel spans
    const stepLabel = { selector: "span.MuiStepLabel-label" };
    expect(screen.getByText("Welcome", stepLabel)).toBeInTheDocument();
    expect(screen.getByText("Connect Repo", stepLabel)).toBeInTheDocument();
    expect(screen.getByText("Create Suite", stepLabel)).toBeInTheDocument();
    expect(screen.getByText("Run Test", stepLabel)).toBeInTheDocument();
    expect(screen.getByText("Notifications", stepLabel)).toBeInTheDocument();
  });

  it("shows a loading spinner while the onboarding state is being fetched", () => {
    pendingState();
    renderWizard();

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("calls onComplete immediately when onboarding is already completed", async () => {
    const onComplete = vi.fn();
    mockGetState.mockResolvedValue({
      data: { completed: true },
    } as any);

    renderWizard(onComplete);

    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
  });

  it("restores server-side progress: step and completed steps", async () => {
    mockGetState.mockResolvedValue({
      data: {
        completed: false,
        current_step: 2,
        steps: { welcome: true, connect_repo: true },
      },
    } as any);

    renderWizard();

    expect(
      await screen.findByText("Create Your First Test Suite"),
    ).toBeInTheDocument();
    // the suite creation form is prefilled with sensible defaults
    const nameInput = screen.getByPlaceholderText(
      "Suite name",
    ) as HTMLInputElement;
    expect(nameInput.value).toBe("My First Test Suite");
    expect(screen.getByRole("button", { name: /create suite/i })).toBeEnabled();
  });

  it("advances to the next step via Continue and persists progress", async () => {
    const user = userEvent.setup();
    renderWizard();

    expect(
      await screen.findByText(/Let's get you started/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /continue/i }));

    await waitFor(() =>
      expect(mockUpdateStep).toHaveBeenCalledWith("welcome", true),
    );
    expect(
      await screen.findByText("Connect Your Repository"),
    ).toBeInTheDocument();
  });

  it("creates a suite from the Create Suite step", async () => {
    mockGetState.mockResolvedValue({
      data: {
        completed: false,
        current_step: 2,
        steps: { welcome: true, connect_repo: true },
      },
    } as any);

    const user = userEvent.setup();
    renderWizard();

    await screen.findByText("Create Your First Test Suite");
    await user.click(screen.getByRole("button", { name: /create suite/i }));

    await waitFor(() => expect(mockCreateSuite).toHaveBeenCalledTimes(1));
    expect(mockCreateSuite.mock.calls[0][0]).toMatchObject({
      name: "My First Test Suite",
      framework_type: "pytest",
    });
    // completing the suite step persists server-side
    await waitFor(() =>
      expect(mockUpdateStep).toHaveBeenCalledWith("create_suite", true),
    );
  });

  it("marks the run_test step complete from the Run Test step", async () => {
    mockGetState.mockResolvedValue({
      data: {
        completed: false,
        current_step: 3,
        steps: { welcome: true, connect_repo: true, create_suite: true },
      },
    } as any);

    const user = userEvent.setup();
    renderWizard();

    expect(await screen.findByText("Run Your First Test")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /mark as complete/i }));

    await waitFor(() =>
      expect(mockUpdateStep).toHaveBeenCalledWith("run_test", true),
    );
  });

  it("finishing the last step completes onboarding and clears the onboarding flag", async () => {
    const onComplete = vi.fn();
    mockGetState.mockResolvedValue({
      data: {
        completed: false,
        current_step: 4,
        steps: {
          welcome: true,
          connect_repo: true,
          create_suite: true,
          run_test: true,
        },
      },
    } as any);

    const user = userEvent.setup();
    renderWizard(onComplete);

    expect(
      await screen.findByText("Configure Notifications"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /finish/i }));

    await waitFor(() =>
      expect(mockUpdateStep).toHaveBeenCalledWith("setup_notifications", true),
    );
    await waitFor(() => expect(mockComplete).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    expect(mockSetNeedsOnboarding).toHaveBeenCalledWith(false);
  });

  it("skipping onboarding calls the skip API and completes the flow", async () => {
    const onComplete = vi.fn();
    const user = userEvent.setup();
    renderWizard(onComplete);

    await screen.findByText(/Welcome to QA-FRAMEWORK/);
    await user.click(screen.getByRole("button", { name: /skip setup/i }));

    await waitFor(() => expect(mockSkip).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    expect(mockSetNeedsOnboarding).toHaveBeenCalledWith(false);
  });

  it("notifies an error when the onboarding state fails to load", async () => {
    mockGetState.mockRejectedValue(new Error("boom"));

    renderWizard();

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        "Failed to load onboarding state",
      ),
    );
  });
});
