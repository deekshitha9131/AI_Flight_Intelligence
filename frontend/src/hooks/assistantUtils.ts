export function getAssistantErrorMessage(error: unknown): string | undefined {
  if (typeof error === "object" && error !== null && "response" in error) {
    const res = (error as { response?: { data?: { message?: string; detail?: string; error?: string }; status?: number } }).response;
    const responseData = res?.data;
    const msg = responseData?.message || responseData?.detail || responseData?.error;
    if (msg) {
      return res?.status ? `[HTTP ${res.status}] ${msg}` : msg;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return undefined;
}
