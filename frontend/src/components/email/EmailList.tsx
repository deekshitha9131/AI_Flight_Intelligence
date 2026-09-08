import { useNavigate } from "react-router-dom";

import type { EmailSummary } from "@/types";

interface EmailListProps {
  emails: EmailSummary[];
}

function formatReceivedAt(receivedAt: string): string {
  return new Date(receivedAt).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function EmailList({ emails }: EmailListProps) {
  const navigate = useNavigate();

  return (
    <div className="divide-y divide-gray-200">
      {emails.map((email) => (
        <div
          key={email.id}
          onClick={() => navigate(`/emails/${email.id}`)}
          className="px-4 py-4 sm:px-6 cursor-pointer hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-start">
                <div className="flex-shrink-0 h-10 w-10">
                  {/* Avatar placeholder */}
                  <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100 6 3 3 0 000-6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-900">
                    {email.sender}
                  </p>
                  <p className="text-sm text-gray-500 line-clamp-1">
                    {email.subject ?? "(no subject)"}
                  </p>
                  {email.snippet && (
                    <p className="mt-1 text-sm text-gray-400 line-clamp-2">
                      {email.snippet}
                    </p>
                  )}
                </div>
              </div>
            </div>
            <div className="ml-4 flex items-center space-x-3 text-sm">
              {email.is_read ? (
                <span className="text-gray-400">
                  ●
                </span>
              ) : (
                <span className="w-2 h-2 bg-blue-500 rounded-full">
                </span>
              )}
              <span className="ml-2 text-gray-400">
                {formatReceivedAt(email.received_at)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default EmailList;