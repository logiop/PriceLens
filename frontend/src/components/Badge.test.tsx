import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge, positionLabel, positionTone, severityLabel, severityTone } from "./Badge";

describe("Badge", () => {
  it("renders its children", () => {
    render(<Badge tone="green">Disponibile</Badge>);
    expect(screen.getByText("Disponibile")).toBeInTheDocument();
  });
});

describe("helpers", () => {
  it("maps severity labels", () => {
    expect(severityLabel("critical")).toBe("Critico");
    expect(severityLabel("warning")).toBe("Avviso");
    expect(severityLabel("info")).toBe("Info");
  });

  it("maps severity tones", () => {
    expect(severityTone("critical")).toBe("red");
    expect(severityTone("warning")).toBe("amber");
    expect(severityTone("info")).toBe("blue");
  });

  it("maps price position", () => {
    expect(positionTone(1)).toBe("green");
    expect(positionTone(2)).toBe("blue");
    expect(positionLabel(3)).toBe("3°");
    expect(positionLabel(null)).toBe("—");
  });
});
