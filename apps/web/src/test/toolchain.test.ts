import { describe, expect, it } from "vitest";

describe("toolchain", () => {
  it("runs TypeScript tests", () => expect("sift-os").toContain("sift"));
});
