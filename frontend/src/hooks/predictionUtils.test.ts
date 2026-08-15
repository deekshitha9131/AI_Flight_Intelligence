import { describe, expect, it } from "vitest";
import { getConfidenceLabel, getPredictionErrorMessage } from "./predictionUtils";

describe("prediction UI helpers", () => {
  it("maps confidence scores to labels", () => {
    expect(getConfidenceLabel(0.9)).toBe("High confidence");
    expect(getConfidenceLabel(0.7)).toBe("Moderate confidence");
    expect(getConfidenceLabel(0.3)).toBe("Watch the trend");
  });

  it("extracts backend error details safely without crashing on null/undefined", () => {
    expect(getPredictionErrorMessage(null)).toBeUndefined();
    expect(getPredictionErrorMessage(undefined)).toBeUndefined();

    const axiosDataMsg = { response: { data: { message: "Prediction failed" } } };
    expect(getPredictionErrorMessage(axiosDataMsg)).toBe("Prediction failed");

    const axiosDataDetail = { response: { data: { detail: "Validation failed" } } };
    expect(getPredictionErrorMessage(axiosDataDetail)).toBe("Validation failed");

    const axiosNoResponse = { message: "Network Error" };
    expect(getPredictionErrorMessage(axiosNoResponse)).toBe("Network Error");

    const jsError = new Error("Custom JS Error");
    expect(getPredictionErrorMessage(jsError)).toBe("Custom JS Error");

    expect(getPredictionErrorMessage("String error message")).toBe("String error message");
  });
});
