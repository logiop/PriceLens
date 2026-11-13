import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceDelta } from "./PriceDelta";

describe("PriceDelta", () => {
  it("renders a positive delta with a plus sign", () => {
    render(<PriceDelta value={5} />);
    expect(screen.getByText("+5.0%")).toBeInTheDocument();
  });

  it("renders a negative delta", () => {
    render(<PriceDelta value={-2.5} />);
    expect(screen.getByText("-2.5%")).toBeInTheDocument();
  });

  it("renders a dash when the value is missing", () => {
    render(<PriceDelta value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
