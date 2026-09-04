import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PlanCard from "./PlanCard";

const freePlan = {
  id: "free",
  name: "Free",
  price: 0,
  interval: "month" as const,
  features: [
    { name: "3 test suites", included: true },
    { name: "AI healing", included: false },
    { name: "Priority support", included: false },
  ],
};

const proPlan = {
  id: "pro",
  name: "Pro",
  price: 29,
  interval: "month" as const,
  popular: true,
  features: [
    { name: "Unlimited suites", included: true },
    { name: "AI healing", included: true },
    { name: "Priority support", included: true },
  ],
};

describe("PlanCard", () => {
  it("renders without crash and shows the plan name", () => {
    render(<PlanCard plan={proPlan} onSelect={() => {}} />);
    expect(screen.getByRole("heading", { name: "Pro" })).toBeInTheDocument();
  });

  it("formats a paid plan price as $<price>/<interval>", () => {
    render(<PlanCard plan={proPlan} onSelect={() => {}} />);
    expect(screen.getByText("$29/month")).toBeInTheDocument();
  });

  it("renders 'Free' without interval suffix for a zero-price plan", () => {
    render(<PlanCard plan={freePlan} onSelect={() => {}} />);
    // the price (not the plan name heading) renders as "Free"
    expect(screen.getByText("Free", { selector: "span" })).toBeInTheDocument();
    expect(screen.queryByText(/Free\/month/i)).not.toBeInTheDocument();
  });

  it("renders all feature names", () => {
    render(<PlanCard plan={freePlan} onSelect={() => {}} />);
    expect(screen.getByText("3 test suites")).toBeInTheDocument();
    expect(screen.getByText("AI healing")).toBeInTheDocument();
    expect(screen.getByText("Priority support")).toBeInTheDocument();
  });

  it("shows the 'Most Popular' badge only for popular plans", () => {
    const { rerender } = render(
      <PlanCard plan={proPlan} onSelect={() => {}} />,
    );
    expect(screen.getByText("Most Popular")).toBeInTheDocument();

    rerender(
      <PlanCard plan={{ ...proPlan, popular: false }} onSelect={() => {}} />,
    );
    expect(screen.queryByText("Most Popular")).not.toBeInTheDocument();
  });

  it("calls onSelect with the plan id when the select button is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<PlanCard plan={proPlan} onSelect={onSelect} />);

    await user.click(screen.getByRole("button", { name: "Select Plan" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("pro");
  });

  it("labels the action 'Downgrade' for a free plan and still selects it", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<PlanCard plan={freePlan} onSelect={onSelect} />);

    await user.click(screen.getByRole("button", { name: "Downgrade" }));
    expect(onSelect).toHaveBeenCalledWith("free");
  });

  it("disables the action and shows 'Current Plan' when the plan is current", async () => {
    const onSelect = vi.fn();
    render(
      <PlanCard plan={{ ...proPlan, current: true }} onSelect={onSelect} />,
    );

    const button = screen.getByRole("button", { name: "Current Plan" });
    // a disabled MUI button has pointer-events: none, so a real user
    // cannot interact with it at all; onSelect can never fire
    expect(button).toBeDisabled();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("disables the action while isLoading", () => {
    const onSelect = vi.fn();
    render(<PlanCard plan={proPlan} onSelect={onSelect} isLoading />);

    expect(screen.getByRole("button", { name: "Select Plan" })).toBeDisabled();
  });
});
