import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SubscriptionStatus from "./SubscriptionStatus";

const daysAgo = (n: number) =>
  new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString();
const daysAhead = (n: number) =>
  new Date(Date.now() + n * 24 * 60 * 60 * 1000).toISOString();

const activeSubscription = {
  id: "sub_1",
  plan_id: "pro",
  plan_name: "Pro",
  status: "active" as const,
  current_period_start: daysAgo(10),
  current_period_end: daysAhead(20),
  cancel_at_period_end: false,
  features: {
    max_suites: 10,
    max_cases: 100,
    ai_healing: true,
    priority_support: true,
  },
  usage: { suites_used: 3, cases_used: 25 },
};

describe("SubscriptionStatus", () => {
  it("renders without crash with an active subscription", () => {
    render(
      <SubscriptionStatus
        subscription={activeSubscription}
        onCancel={() => {}}
        onUpgrade={() => {}}
      />,
    );
    expect(screen.getByText("Pro")).toBeInTheDocument();
  });

  it("shows the free-plan empty state when subscription is null", () => {
    render(
      <SubscriptionStatus
        subscription={null}
        onCancel={() => {}}
        onUpgrade={() => {}}
      />,
    );
    expect(screen.getByText("No Active Subscription")).toBeInTheDocument();
    expect(screen.getByText(/free plan/i)).toBeInTheDocument();
  });

  it("calls onUpgrade from the empty state", async () => {
    const onUpgrade = vi.fn();
    const user = userEvent.setup();
    render(
      <SubscriptionStatus
        subscription={null}
        onCancel={() => {}}
        onUpgrade={onUpgrade}
      />,
    );

    await user.click(screen.getByRole("button", { name: /upgrade plan/i }));
    expect(onUpgrade).toHaveBeenCalledTimes(1);
  });

  it("shows the status chip and the billing period for an active subscription", () => {
    render(
      <SubscriptionStatus
        subscription={activeSubscription}
        onCancel={() => {}}
        onUpgrade={() => {}}
      />,
    );
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Current billing period")).toBeInTheDocument();
    // both period dates are rendered as a single "<start> - <end>" string
    expect(
      screen.getByText(
        /^[A-Z][a-z]{2} \d{1,2}, \d{4} - [A-Z][a-z]{2} \d{1,2}, \d{4}$/,
      ),
    ).toBeInTheDocument();
  });

  it("renders usage counters for suites and cases", () => {
    render(
      <SubscriptionStatus
        subscription={activeSubscription}
        onCancel={() => {}}
        onUpgrade={() => {}}
      />,
    );
    expect(screen.getByText("Usage This Period")).toBeInTheDocument();
    expect(screen.getByText("Test Suites")).toBeInTheDocument();
    expect(screen.getByText("3/10")).toBeInTheDocument();
    expect(screen.getByText("Test Cases")).toBeInTheDocument();
    expect(screen.getByText("25/100")).toBeInTheDocument();
  });

  it("calls onUpgrade from Change Plan and onCancel from Cancel Subscription", async () => {
    const onCancel = vi.fn();
    const onUpgrade = vi.fn();
    const user = userEvent.setup();
    render(
      <SubscriptionStatus
        subscription={activeSubscription}
        onCancel={onCancel}
        onUpgrade={onUpgrade}
      />,
    );

    await user.click(screen.getByRole("button", { name: /change plan/i }));
    expect(onUpgrade).toHaveBeenCalledTimes(1);

    await user.click(
      screen.getByRole("button", { name: /cancel subscription/i }),
    );
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("shows the cancellation warning and hides the cancel action when cancel_at_period_end is true", () => {
    render(
      <SubscriptionStatus
        subscription={{
          ...activeSubscription,
          cancel_at_period_end: true,
        }}
        onCancel={() => {}}
        onUpgrade={() => {}}
      />,
    );

    expect(
      screen.getByText(/canceled at the end of the current billing period/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /cancel subscription/i }),
    ).not.toBeInTheDocument();
    // Change Plan remains available
    expect(screen.getByRole("button", { name: /change plan/i })).toBeEnabled();
  });

  it("disables the actions while isLoading", () => {
    render(
      <SubscriptionStatus
        subscription={activeSubscription}
        onCancel={() => {}}
        onUpgrade={() => {}}
        isLoading
      />,
    );
    expect(screen.getByRole("button", { name: /change plan/i })).toBeDisabled();
    expect(
      screen.getByRole("button", { name: /cancel subscription/i }),
    ).toBeDisabled();
  });
});
