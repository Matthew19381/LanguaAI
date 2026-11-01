import { describe, it, expect } from "vitest"
import { localDay } from "../localDay"

describe("localDay", () => {
  it("uses the local calendar day, not the UTC one", () => {
    const d = new Date(2026, 10, 1, 0, 30)  // 00:30 local time
    expect(localDay(d)).toBe("2026-11-01")
  })
})
