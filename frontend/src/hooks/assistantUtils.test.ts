import { describe, expect, it } from "vitest";
import { getAssistantErrorMessage } from "./assistantUtils";

describe("assistant UI helpers", () => {
  it("extracts the backend error message", () => {
    const error = { response: { data: { detail: "Assistant unavailable" } } };
    expect(getAssistantErrorMessage(error)).toBe("Assistant unavailable");
  });
});
