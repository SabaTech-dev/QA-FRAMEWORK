import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import KeyboardShortcutsDialog from "./KeyboardShortcutsDialog";
import { DEFAULT_SHORTCUTS } from "../../hooks/useKeyboardShortcuts";

describe("KeyboardShortcutsDialog", () => {
  it("renders the dialog title when open", () => {
    render(<KeyboardShortcutsDialog open onClose={() => {}} />);
    expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    render(<KeyboardShortcutsDialog open={false} onClose={() => {}} />);
    expect(screen.queryByText("Keyboard Shortcuts")).not.toBeInTheDocument();
  });

  it("groups shortcuts by category with one heading per category", () => {
    render(<KeyboardShortcutsDialog open onClose={() => {}} />);

    const expectedCategories = [
      ...new Set(DEFAULT_SHORTCUTS.map((s) => s.category)),
    ];
    for (const category of expectedCategories) {
      expect(screen.getByText(category)).toBeInTheDocument();
    }
  });

  it("renders every shortcut description", () => {
    render(<KeyboardShortcutsDialog open onClose={() => {}} />);

    for (const shortcut of DEFAULT_SHORTCUTS) {
      expect(
        screen.getByText(shortcut.description),
      ).toBeInTheDocument();
    }
  });

  it("renders each shortcut key as an uppercase chip", () => {
    render(<KeyboardShortcutsDialog open onClose={() => {}} />);

    for (const shortcut of DEFAULT_SHORTCUTS) {
      expect(
        screen.getByText(shortcut.key.toUpperCase()),
      ).toBeInTheDocument();
    }
  });

  it("lists the Navigation category shortcuts under their heading", () => {
    render(<KeyboardShortcutsDialog open onClose={() => {}} />);

    const navigation = screen.getByText("Navigation", { exact: true });
    const section = navigation.closest("div");
    expect(section).not.toBeNull();
    expect(section).toHaveTextContent("Focus search");
    expect(section).toHaveTextContent("Go to home");
    expect(section).toHaveTextContent("Close dialog/modal");
  });

  it("calls onClose when the close icon is clicked", async () => {
    const onClose = vi.fn();
    render(<KeyboardShortcutsDialog open onClose={onClose} />);

    // the close IconButton is the only button rendered by the dialog
    fireEvent.click(screen.getByRole("button"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on Escape key (MUI dialog contract)", () => {
    const onClose = vi.fn();
    render(<KeyboardShortcutsDialog open onClose={onClose} />);

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
