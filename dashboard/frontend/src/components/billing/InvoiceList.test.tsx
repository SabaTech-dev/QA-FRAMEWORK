import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InvoiceList from "./InvoiceList";

const invoices = [
  {
    id: "inv_1",
    number: "INV-001",
    amount: 4900,
    currency: "usd",
    status: "paid" as const,
    created_at: "2025-01-15T10:00:00Z",
    invoice_url: "https://billing.example.com/invoices/inv_1.pdf",
  },
  {
    id: "inv_2",
    number: "INV-002",
    amount: 1299,
    currency: "eur",
    status: "open" as const,
    created_at: "2025-02-15T10:00:00Z",
  },
];

describe("InvoiceList", () => {
  it("renders without crash and shows the table heading with invoices", () => {
    render(<InvoiceList invoices={invoices} />);
    expect(
      screen.getByRole("heading", { name: "Invoice History" }),
    ).toBeInTheDocument();
  });

  it("shows a loading spinner while isLoading", () => {
    render(<InvoiceList invoices={[]} isLoading />);
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.queryByText("Invoice History")).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no invoices", () => {
    render(<InvoiceList invoices={[]} />);
    expect(screen.getByText("No invoices yet")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("renders one row per invoice with number, formatted amount, status and date", () => {
    render(<InvoiceList invoices={invoices} />);

    expect(screen.getByText("#INV-001")).toBeInTheDocument();
    expect(screen.getByText("#INV-002")).toBeInTheDocument();

    // amount is in cents: 4900 usd -> $49.00, 1299 eur -> €12.99
    expect(screen.getByText("$49.00")).toBeInTheDocument();
    expect(screen.getByText("€12.99")).toBeInTheDocument();

    expect(screen.getByText("paid")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();

    expect(screen.getByText("Jan 15, 2025")).toBeInTheDocument();
    expect(screen.getByText("Feb 15, 2025")).toBeInTheDocument();
  });

  it("renders a download link only for invoices with an invoice_url", () => {
    render(<InvoiceList invoices={invoices} />);

    // the download action is an icon-only IconButton rendered as an anchor;
    // it has no accessible name, so query all links in the table
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute(
      "href",
      "https://billing.example.com/invoices/inv_1.pdf",
    );
    expect(links[0]).toHaveAttribute("target", "_blank");
    expect(links[0]).toHaveAttribute("rel", "noopener noreferrer");
  });
});
