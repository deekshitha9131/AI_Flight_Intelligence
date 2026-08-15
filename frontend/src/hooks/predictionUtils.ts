export function getConfidenceLabel(confidenceScore?: number | null) {
  const score = typeof confidenceScore === "number" ? confidenceScore : 0;
  if (score >= 0.8) return "High confidence";
  if (score >= 0.6) return "Moderate confidence";
  return "Watch the trend";
}

export function getPredictionErrorMessage(error: unknown): string | undefined {
  if (!error) {
    return undefined;
  }

  // Temporary logging so the original API error can be inspected in the browser console
  console.error("[Prediction API Error]:", error);

  if (typeof error === "object" && error !== null) {
    const errObj = error as {
      response?: {
        data?: {
          message?: string;
          detail?: string | Array<{ msg?: string }>;
          error?: string;
        };
      };
      message?: string;
    };

    const responseData = errObj.response?.data;
    if (responseData) {
      if (typeof responseData.message === "string" && responseData.message) {
        return responseData.message;
      }
      if (typeof responseData.detail === "string" && responseData.detail) {
        return responseData.detail;
      }
      if (Array.isArray(responseData.detail) && responseData.detail.length > 0) {
        const first = responseData.detail[0];
        if (typeof first === "object" && first?.msg) {
          return first.msg;
        }
      }
      if (typeof responseData.error === "string" && responseData.error) {
        return responseData.error;
      }
    }

    if (typeof errObj.message === "string" && errObj.message) {
      return errObj.message;
    }
  }

  if (typeof error === "string" && error.trim()) {
    return error;
  }

  return undefined;
}
