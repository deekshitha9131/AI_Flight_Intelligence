import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { analyzeEmail, createDraft } from "@/api";
import { ApiError } from "@/api/client";
import DraftEditor from "@/components/draft/DraftEditor";
import EmailDetailView from "@/components/email/EmailDetailView";
import { useEmailDetail } from "@/hooks/useEmailDetail";
import type { AIUnderstandingResult, Draft } from "@/types";

type DraftGenerationStatus = "idle" | "generating" | "success" | "not_analyzed" | "error";

function EmailDetail() {
  const { emailId } = useParams<{ emailId: string }>();
  const { status, email, retry } = useEmailDetail(emailId ?? "");
  const [draftStatus, setDraftStatus] = useState<DraftGenerationStatus>("idle");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [analysisResult, setAnalysisResult] = useState<AIUnderstandingResult | null>(null);

  async function handleGenerateDraft() {
    if (!email || draftStatus === "generating") return;
    setDraftStatus("generating");
    try {
      const generated = await createDraft({ email_id: email.id });
      setDraft(generated);
      setDraftStatus("success");
    } catch (error) {
      setDraftStatus(error instanceof ApiError && error.code === "DRAFT_UNDERSTANDING_MISSING" ? "not_analyzed" : "error");
    }
  }

  const handleAnalyzeEmail = useCallback(async () => {
    if (!email || !emailId || analysisStatus === "loading") return;
    setAnalysisStatus("loading");
    try {
      const result = await analyzeEmail(emailId);
      setAnalysisResult(result);
      setAnalysisStatus("success");
    } catch (error) {
      console.error("AI analysis failed:", error);
      setAnalysisStatus("error");
    }
  }, [analysisStatus, email, emailId]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container py-8">
        <div className="mb-6 flex items-center justify-between">
          <Link to="/inbox" className="flex items-center text-sm text-gray-600 hover:text-gray-900">
            Back to Inbox
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Email Details</h1>
        </div>

        {status === "loading" && <p className="text-center py-12 text-gray-600">Loading email...</p>}
        {status === "not_found" && <p className="text-center py-12 text-gray-600">This email is not available.</p>}
        {status === "error" && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
            <p className="text-red-700">We could not load this email. Please try again.</p>
            <button type="button" onClick={retry} className="mt-2 px-3 py-2 bg-red-100 text-red-800 rounded-md">
              Retry
            </button>
          </div>
        )}

        {status === "success" && email && (
          <>
            <div className="mb-6">
              <EmailDetailView email={email} />
            </div>

            <section className="mb-6 space-y-4">
              <button
                type="button"
                onClick={handleAnalyzeEmail}
                disabled={analysisStatus === "loading"}
                className="w-full px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-800 font-medium rounded-lg"
              >
                {analysisStatus === "loading" ? "Analyzing..." : "Analyze with AI"}
              </button>
              {analysisStatus === "success" && analysisResult && (
                <div className="p-4 bg-white rounded-xl shadow-md space-y-2">
                  <h2 className="text-lg font-semibold text-gray-900">AI Analysis</h2>
                  <p className="text-sm text-gray-600">{analysisResult.summary}</p>
                  <p className="text-sm text-gray-600">Category: {analysisResult.category}</p>
                  <p className="text-sm text-gray-600">Sentiment: {analysisResult.sentiment}</p>
                </div>
              )}
              {analysisStatus === "error" && <p className="text-red-700">Unable to analyze this email.</p>}
            </section>

            {!draft && (
              <button
                type="button"
                onClick={handleGenerateDraft}
                disabled={draftStatus === "generating"}
                className="w-full px-4 py-2 bg-green-50 hover:bg-green-100 text-green-800 font-medium rounded-lg"
              >
                {draftStatus === "generating" ? "Generating reply..." : "Generate Reply"}
              </button>
            )}
            {draftStatus === "not_analyzed" && <p className="mt-3 text-gray-600">Analyze the email before generating a reply.</p>}
            {draftStatus === "error" && <p className="mt-3 text-red-700">Unable to generate a reply.</p>}
            {draft && <div className="mt-6"><DraftEditor draft={draft} onDraftChange={setDraft} /></div>}
          </>
        )}
      </div>
    </div>
  );
}

export default EmailDetail;