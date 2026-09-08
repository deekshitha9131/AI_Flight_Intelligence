import { useState } from "react";

import { loginUrl } from "@/api/auth";

function Login() {
  const [error, setError] = useState<string | null>(null);
  const [isStartingLogin, setIsStartingLogin] = useState(false);

  async function handleContinueWithGoogle() {
    setError(null);
    setIsStartingLogin(true);

    try {
      const response = await fetch(loginUrl, {
        credentials: "include",
        redirect: "manual",
      });

      if (response.status === 503) {
        const body = await response.json();
        setError(body.error?.message ?? "Google login is not configured.");
        return;
      }

      if (response.type === "opaqueredirect" || (response.status >= 300 && response.status < 400)) {
        window.location.href = loginUrl;
        return;
      }

      setError("Google login could not be started. Please try again.");
    } catch {
      setError("The backend is unavailable. Please start the API and try again.");
    } finally {
      setIsStartingLogin(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
      <div className="w-full max-w-md space-y-8 p-6">
        <div className="text-center">
          <h1 className="mb-4 text-3xl font-bold text-gray-900">
            AI Email Assistant
          </h1>
          <p className="mb-6 text-gray-600">
            Your intelligent email companion that analyzes, understands, and drafts replies
            to your Gmail messages with AI-powered assistance.
          </p>
        </div>

        <div className="space-y-4">
          <button
            onClick={handleContinueWithGoogle}
            disabled={isStartingLogin}
            type="button"
            className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200"
          >
            {isStartingLogin ? "Connecting..." : "Continue with Google"}
          </button>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <p className="text-xs text-gray-500">
            We never store your password and only request access to read and send emails
            on your behalf.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;