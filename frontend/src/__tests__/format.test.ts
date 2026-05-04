import { describe, it, expect } from "vitest";
import {
  formatCurrency,
  formatCompactCurrency,
  formatPercent,
  formatPrice,
  formatQuantity,
} from "@/lib/format";

describe("formatCurrency", () => {
  it("formats positive values with dollar sign and two decimals", () => {
    expect(formatCurrency(10000)).toBe("$10,000.00");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toBe("$0.00");
  });

  it("formats negative values", () => {
    expect(formatCurrency(-500.5)).toBe("-$500.50");
  });

  it("rounds to two decimal places", () => {
    expect(formatCurrency(123.456)).toBe("$123.46");
  });
});

describe("formatCompactCurrency", () => {
  it("formats thousands with K suffix", () => {
    const result = formatCompactCurrency(10000);
    expect(result).toMatch(/\$10\.0K/);
  });

  it("formats small values without suffix", () => {
    const result = formatCompactCurrency(500);
    expect(result).toMatch(/\$500/);
  });
});

describe("formatPercent", () => {
  it("formats positive percent with sign", () => {
    const result = formatPercent(2.56);
    expect(result).toMatch(/\+2\.56%/);
  });

  it("formats negative percent with sign", () => {
    const result = formatPercent(-1.23);
    expect(result).toMatch(/-1\.23%/);
  });

  it("divides input by 100 before formatting", () => {
    // formatPercent(100) should give +100.00% since Intl percent multiplies by 100
    // and we divide by 100 first, so 100 / 100 = 1.0 → 100%
    const result = formatPercent(100);
    expect(result).toMatch(/\+100\.00%/);
  });
});

describe("formatPrice", () => {
  it("formats to two decimal places", () => {
    expect(formatPrice(190.25)).toBe("190.25");
  });

  it("pads with trailing zeros", () => {
    expect(formatPrice(100)).toBe("100.00");
  });

  it("rounds correctly", () => {
    expect(formatPrice(99.999)).toBe("100.00");
  });
});

describe("formatQuantity", () => {
  it("formats integer quantities without decimals", () => {
    expect(formatQuantity(10)).toBe("10");
  });

  it("formats fractional quantities with two decimals", () => {
    expect(formatQuantity(10.5)).toBe("10.50");
  });

  it("formats zero", () => {
    expect(formatQuantity(0)).toBe("0");
  });
});
