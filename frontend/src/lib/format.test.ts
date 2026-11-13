import { describe, expect, it } from "vitest";
import { formatPct, formatPrice, relativeTime } from "./format";

describe("formatPrice", () => {
  it("formats an amount as EUR", () => {
    expect(formatPrice(1234.5)).toContain("234,50");
    expect(formatPrice(1234.5)).toContain("€");
  });

  it("returns a dash for null/undefined", () => {
    expect(formatPrice(null)).toBe("—");
    expect(formatPrice(undefined)).toBe("—");
  });
});

describe("formatPct", () => {
  it("adds a sign for positive values", () => {
    expect(formatPct(5)).toBe("+5.0%");
    expect(formatPct(-3.2)).toBe("-3.2%");
    expect(formatPct(0)).toBe("0.0%");
  });

  it("can omit the sign", () => {
    expect(formatPct(15, false)).toBe("15.0%");
  });

  it("handles null", () => {
    expect(formatPct(null)).toBe("—");
  });
});

describe("relativeTime", () => {
  it("says 'adesso' for the present", () => {
    expect(relativeTime(new Date().toISOString())).toBe("adesso");
  });

  it("formats minutes and hours", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60_000).toISOString();
    expect(relativeTime(fiveMinAgo)).toBe("5 min fa");
    const twoHoursAgo = new Date(Date.now() - 2 * 3600_000).toISOString();
    expect(relativeTime(twoHoursAgo)).toBe("2 h fa");
  });
});
