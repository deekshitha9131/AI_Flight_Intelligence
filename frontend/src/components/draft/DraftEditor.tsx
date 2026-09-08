import { useState } from "react";

import { ApiError } from "@/api/client";
import { approveDraft, updateDraft } from "@/api/drafts";
import type { Draft } from "@/types";

type SaveStatus = "idle" | "saving" | "saved" | "error";
type ApproveStatus = "idle" | "approving" | "error";

interface DraftEditorProps {
  draft: Draft;
  onDraftChange: (draft: Draft) => void;
}

function DraftEditor({ draft, onDraftChange }: DraftEditorProps) {
  const [body, setBody] = useState(draft.body);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [approveStatus, setApproveStatus] = useState<ApproveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [approveError, setApproveError] = useState<string | null>(null);

  const isFinal = draft.status !== "generated";
  const isBusy = saveStatus === "saving" || approveStatus === "approving";

  async function handleSave() {
    if (isBusy || isFinal) return;
    setSaveStatus("saving");
    setSaveError(null);
    try {
      const updated = await updateDraft(draft.id, { body });
      onDraftChange(updated);
      setBody(updated.body);
      setSaveStatus("saved");
    } catch (err) {
      setSaveStatus("error");
      setSaveError(describeError(err, "save"));
      // body (the user's local edit) is intentionally left untouched.
    }
  }

  async function handleApprove() {
    if (isBusy || isFinal) return;
    setApproveStatus("approving");
    setApproveError(null);
    try {
      const updated = await approveDraft(draft.id);
      onDraftChange(updated);
      setApproveStatus("idle");
    } catch (err) {
      setApproveStatus("error");
      setApproveError(describeError(err, "approve"));
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Generated Reply
        </h2>
        <textarea
          value={body}
          onChange={(e) => {
            setBody(e.target.value);
            setSaveStatus("idle");
          }}
          disabled={isBusy || isFinal}
          className="w-full min-h-[80px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-y"
          rows={10}
        />
      </div>

      <div className="flex items-center space-x-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={isBusy || isFinal}
          className="flex-1 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-800 font-medium rounded-md transition-colors"
        >
          {saveStatus === "saving" ? (
            <>
              <svg className="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l4 4H6l4-4z" />
              </svg>
              Saving...
            </>
          ) : (
            "Save Draft"
          )}
        </button>
        <button
          type="button"
          onClick={handleApprove}
          disabled={isBusy || isFinal}
          className="flex-1 px-3 py-2 bg-green-50 hover:bg-green-100 text-green-800 font-medium rounded-md transition-colors ml-2"
        >
          {approveStatus === "approving" ? (
            <>
              <svg className="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l4 4H6l4-4z" />
              </svg>
              Approving...
            </>
          ) : (
            "Approve"
          )}
        </button>
      </div>

      <div className="flex items-center space-x-2 text-sm">
        {saveStatus === "saved" && (
          <span className="text-green-600">
            Saved.
          </span>
        )}
        {draft.status === "approved" && (
          <span className="text-green-600 font-medium">
            Draft Approved
          </span>
        )}
      </div>

      {saveStatus === "error" && (
        <div className="mt-2 bg-red-50 border-l-4 border-red-400 p-3">
          <p className="text-red-700">{saveError}</p>
          <button
            type="button"
            onClick={handleSave}
            className="mt-2 w-full inline-flex items-center justify-center px-3 py-2 bg-red-100 text-red-800 font-medium rounded-md hover:bg-red-200"
          >
            Retry Save
          </button>
        </div>
      )}

      {approveStatus === "error" && (
        <div className="mt-2 bg-red-50 border-l-4 border-red-400 p-3">
          <p className="text-red-700">{approveError}</p>
          <button
            type="button"
            onClick={handleApprove}
            className="mt-2 w-full inline-flex items-center justify-center px-3 py-2 bg-red-100 text-red-800 font-medium rounded-md hover:bg-red-200"
          >
            Retry Approve
          </button>
        </div>
      )}

      {isFinal && draft.status !== "approved" && (
        <div className="mt-2 bg-yellow-50 border-l-4 border-yellow-400 p-3">
          <p className="text-yellow-700">
            This draft is {draft.status} and can no longer be edited.
          </p>
        </div>
      )}
    </div>
  );
}

export default DraftEditor;

function describeError(err: unknown, action: "save" | "approve"): string {
  if (err instanceof ApiError && err.status === 404) {
    return `Unable to ${action} draft: this feature is not yet available on the server.`;
  }
  return `Unable to ${action} draft. Please try again.`;
}