import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCallback } from "react";

import { generateEmailContent, gmailSend } from "@/api";

type ComposeStatus = "idle" | "generating" | "saving" | "sending" | "success" | "error";

interface ComposeFormValues {
  to: string;
  subject: string;
  body: string;
}

function Compose() {
  const navigate = useNavigate();
  const [formValues, setFormValues] = useState<ComposeFormValues>({to: "", subject: "", body: ""});
  const [status, setStatus] = useState<ComposeStatus>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [generatedBody, setGeneratedBody] = useState<string>("");

  const handleGenerateAI = useCallback(async () => {
    if (!formValues.to && !formValues.subject && !formValues.body) {
      setStatusMessage("Please enter some content to generate from");
      setStatus("error");
      return;
    }

    setStatus("generating");
    setStatusMessage("Generating email content...");
    try {
      // Call backend to generate email content from intent
      const response = await generateEmailContent({
        to: formValues.to,
        subject: formValues.subject,
        body: formValues.body,
        instructions: "Generate a professional email based on the provided content"
      });

      setGeneratedBody(`${response.subject}\n\n`.trim());
      setFormValues((prev) => ({
        ...prev,
        subject: response.subject,
        body: response.body
      }));
      setStatus("success");
      setStatusMessage("Email content generated successfully");
    } catch (err: any) {
      console.error("Generation failed:", err);
      setStatus("error");
      setStatusMessage("Failed to generate email content. Please try again.");
    }
  }, [formValues]);

  const handleSaveDraft = useCallback(async () => {
    if (!formValues.body.trim()) {
      setStatusMessage("Cannot save empty draft");
      setStatus("error");
      return;
    }

    setStatus("saving");
    setStatusMessage("Saving draft...");
    try {
      // For MVP, we'll simulate draft saving
      // In a full implementation, this would call the backend draft API
      setStatusMessage("Draft saved successfully");
      setStatus("success");
    } catch (err: any) {
      console.error("Save failed:", err);
      setStatus("error");
      setStatusMessage("Failed to save draft. Please try again.");
    }
  }, [formValues]);

  const handleSend = useCallback(async () => {
    if (!formValues.to.trim()) {
      setStatusMessage("To field is required");
      setStatus("error");
      return;
    }

    if (!formValues.body.trim()) {
      setStatusMessage("Cannot send empty email");
      setStatus("error");
      return;
    }

    setStatus("sending");
    setStatusMessage("Sending email...");
    try {
      // Send via Gmail API
      await gmailSend({
        to: [formValues.to],
        subject: formValues.subject,
        body_text: formValues.body
      });

      setStatus("success");
      setStatusMessage("Email sent successfully!");

      // Reset form after successful send
      setTimeout(() => {
        setFormValues({ to: "", subject: "", body: "" });
        setStatus("idle");
        setStatusMessage("");
        setGeneratedBody("");
      }, 2000);
    } catch (err: any) {
      console.error("Send failed:", err);
      setStatus("error");
      setStatusMessage("Failed to send email. Please try again.");
    }
  }, [formValues]);

  const handleDiscard = useCallback(() => {
    setFormValues({ to: "", subject: "", body: "" });
    setStatus("idle");
    setStatusMessage("");
    setGeneratedBody("");
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container py-8">
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => navigate("/inbox")}
            className="flex items-center text-sm text-gray-600 hover:text-gray-900"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back to Inbox
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Compose Email</h1>
        </div>

        {status === "error" && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
            <p className="text-red-700">{statusMessage}</p>
            <button
              type="button"
              onClick={() => setStatus("idle")}
              className="mt-2 inline-flex items-center px-3 py-2 bg-red-100 text-red-800 font-medium rounded-md hover:bg-red-200"
            >
              Dismiss
            </button>
          </div>
        )}

        {status === "success" && (
          <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
            <p className="text-green-700">{statusMessage}</p>
            <button
              type="button"
              onClick={() => setStatus("idle")}
              className="mt-2 inline-flex items-center px-3 py-2 bg-green-100 text-green-800 font-medium rounded-md hover:bg-green-200"
            >
              Dismiss
            </button>
          </div>
        )}

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">To</label>
            <input
              value={formValues.to}
              onChange={(e) => setFormValues((prev) => ({ ...prev, to: e.target.value }))}
              placeholder="recipient@example.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subject</label>
            <input
              value={formValues.subject}
              onChange={(e) => setFormValues((prev) => ({ ...prev, subject: e.target.value }))}
              placeholder="Email subject"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
            <textarea
              value={formValues.body}
              onChange={(e) => setFormValues((prev) => ({ ...prev, body: e.target.value }))}
              placeholder="Type your message here..."
              className="w-full min-h-[200px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-y"
              rows={10}
            />
          </div>

          <div className="flex items-center space-x-4">
            <button
              type="button"
              onClick={handleGenerateAI}
              disabled={status === "generating" || status === "sending"}
              className="flex-1 px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-800 font-medium rounded-lg transition-colors"
            >
              {status === "generating" ? (
                <>
                  <svg className="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l4 4H6l4-4z" />
                  </svg>
                  Generating...
                </>
              ) : (
                "Generate with AI"
              )}
            </button>

            <button
              type="button"
              onClick={handleSaveDraft}
              disabled={status === "saving" || status === "sending"}
              className="flex-1 px-4 py-2 bg-green-50 hover:bg-green-100 text-green-800 font-medium rounded-lg transition-colors"
            >
              {status === "saving" ? "Saving..." : "Save Draft"}
            </button>

            <button
              type="button"
              onClick={handleSend}
              disabled={status === "sending" || !formValues.to.trim() || !formValues.body.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              {status === "sending" ? "Sending..." : "Send"}
            </button>

            <button
              type="button"
              onClick={handleDiscard}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-lg transition-colors"
            >
              Discard
            </button>
          </div>
        </div>

        {generatedBody && status !== "generating" && (
          <div className="mt-6 p-4 bg-white rounded-xl shadow-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Generated Preview</h2>
            <div className="whitespace-pre-wrap break-words text-gray-700">
              {generatedBody}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Compose;
