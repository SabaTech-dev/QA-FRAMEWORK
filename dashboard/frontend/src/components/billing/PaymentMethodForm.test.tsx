import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PaymentMethodForm from "./PaymentMethodForm";

const fillCardFields = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.type(screen.getByLabelText(/card number/i), "4242424242424242");
  await user.type(screen.getByLabelText(/expiry/i), "1230");
  await user.type(screen.getByLabelText(/^cvc/i), "123");
};

describe("PaymentMethodForm", () => {
  it("renders without crash and shows the dialog title when open", () => {
    render(<PaymentMethodForm open onClose={() => {}} onSubmit={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Add Payment Method")).toBeInTheDocument();
  });

  it("disables the Add Card button until all fields are filled", async () => {
    const user = userEvent.setup();
    render(<PaymentMethodForm open onClose={() => {}} onSubmit={vi.fn()} />);

    const addButton = screen.getByRole("button", { name: /add card/i });
    expect(addButton).toBeDisabled();

    await user.type(screen.getByLabelText(/card number/i), "4242424242424242");
    expect(addButton).toBeDisabled();

    await user.type(screen.getByLabelText(/expiry/i), "1230");
    expect(addButton).toBeDisabled();

    await user.type(screen.getByLabelText(/^cvc/i), "123");
    expect(addButton).toBeEnabled();
  });

  it("formats the card number into groups of 4 digits while typing", async () => {
    const user = userEvent.setup();
    render(<PaymentMethodForm open onClose={() => {}} onSubmit={vi.fn()} />);

    await user.type(screen.getByLabelText(/card number/i), "4242424242424242");
    expect(screen.getByLabelText(/card number/i)).toHaveValue(
      "4242 4242 4242 4242",
    );
  });

  it("formats expiry as MM/YY while typing", async () => {
    const user = userEvent.setup();
    render(<PaymentMethodForm open onClose={() => {}} onSubmit={vi.fn()} />);

    await user.type(screen.getByLabelText(/expiry/i), "1230");
    expect(screen.getByLabelText(/expiry/i)).toHaveValue("12/30");
  });

  it("strips non-digit characters from CVC", async () => {
    const user = userEvent.setup();
    render(<PaymentMethodForm open onClose={() => {}} onSubmit={vi.fn()} />);

    await user.type(screen.getByLabelText(/^cvc/i), "12a3");
    expect(screen.getByLabelText(/^cvc/i)).toHaveValue("123");
  });

  it("submits a payment method id and closes the dialog on success", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();
    render(<PaymentMethodForm open onClose={onClose} onSubmit={onSubmit} />);

    await fillCardFields(user);
    await user.click(screen.getByRole("button", { name: /add card/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0]).toMatch(/^pm_/);
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("shows an error alert and keeps the dialog open when onSubmit fails", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onSubmit = vi.fn().mockRejectedValue({
      response: { data: { detail: "Card declined" } },
    });
    render(<PaymentMethodForm open onClose={onClose} onSubmit={onSubmit} />);

    await fillCardFields(user);
    await user.click(screen.getByRole("button", { name: /add card/i }));

    expect(await screen.findByText("Card declined")).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("falls back to a generic error message when the failure has no detail", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue(new Error("network down"));
    render(<PaymentMethodForm open onClose={() => {}} onSubmit={onSubmit} />);

    await fillCardFields(user);
    await user.click(screen.getByRole("button", { name: /add card/i }));

    expect(
      await screen.findByText("Failed to add payment method"),
    ).toBeInTheDocument();
  });

  it("shows a loading state on the action buttons while submitting", async () => {
    const user = userEvent.setup();
    let resolveSubmit: () => void = () => {};
    const onSubmit = vi.fn().mockReturnValue(
      new Promise<void>((resolve) => {
        resolveSubmit = resolve;
      }),
    );
    const onClose = vi.fn();
    render(<PaymentMethodForm open onClose={onClose} onSubmit={onSubmit} />);

    await fillCardFields(user);
    await user.click(screen.getByRole("button", { name: /add card/i }));

    // while the submit promise is pending the dialog is in loading state
    await waitFor(() =>
      expect(screen.getByRole("progressbar")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: /cancel/i })).toBeDisabled();

    resolveSubmit();
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("closes the dialog via the Cancel button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<PaymentMethodForm open onClose={onClose} onSubmit={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
