import { useEffect, useState } from "react";

import EmailList from "@/components/email/EmailList";
import { gmailSync } from "@/api";
import { useAuth } from "@/hooks/useAuth";
import { useEmails } from "@/hooks/useEmails";

function Inbox() {
  const { user } = useAuth();
  const { status, emails, page, pageSize, total, isEmpty, errorMessage, setPage, retry } =
    useEmails();
  const [syncStatus, setSyncStatus] = useState("idle");
  const [syncError, setSyncError] = useState<string | null>(null);
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    if (!user) {
      return;
    }

    void syncInitialEmails();
  }, [user]);

  async function syncInitialEmails() {
    setSyncStatus("syncing");
    setSyncError(null);
    try {
      await gmailSync();
      setSyncStatus("success");
    } catch (error) {
      console.error("Gmail sync failed:", error);
      setSyncStatus("error");
      setSyncError("Failed to sync emails. Please try again.");
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
          <p className="text-gray-600">
            Your AI-powered email assistant is ready to help you manage your inbox.
          </p>
        </div>

        {syncStatus === "syncing" && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto" />
            <p className="mt-4 text-gray-600">Syncing your emails...</p>
          </div>
        )}

        {syncStatus === "error" && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
            <p className="text-red-700">{syncError}</p>
            <button
              type="button"
              onClick={syncInitialEmails}
              className="mt-2 inline-flex items-center px-3 py-2 bg-red-100 text-red-800 font-medium rounded-md hover:bg-red-200"
            >
              Retry Sync
            </button>
          </div>
        )}

        {status === "loading" && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto" />
            <p className="mt-4 text-gray-600">Loading your inbox...</p>
          </div>
        )}

        {status === "error" && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
            <p className="text-red-700">{errorMessage}</p>
            <button
              type="button"
              onClick={retry}
              className="mt-2 inline-flex items-center px-3 py-2 bg-red-100 text-red-800 font-medium rounded-md hover:bg-red-200"
            >
              Retry
            </button>
          </div>
        )}

        {status === "success" && isEmpty && (
          <div className="text-center py-12">
            <p className="mt-4 text-gray-600">
              {user
                ? "Your inbox is empty. Emails will appear here once they arrive in your Gmail account."
                : "Please connect your Gmail account to see your emails here."}
            </p>
          </div>
        )}

        {status === "success" && !isEmpty && (
          <>
            <div className="mb-4">
              <EmailList emails={emails} />
            </div>
            <div className="flex items-center justify-between px-4">
              <div className="text-sm text-gray-500">
                Showing {emails.length} of {total} emails
              </div>
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-md disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-3 py-1 bg-white text-gray-600 rounded-md">
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                  className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-md disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Inbox;