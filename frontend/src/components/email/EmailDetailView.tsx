import type { EmailDetail } from "@/types";

interface EmailDetailViewProps {
  email: EmailDetail;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function EmailDetailView({ email }: EmailDetailViewProps) {
  const bodyText = email.body_text ?? email.body_html ?? "(no body content)";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          {email.subject ?? "(no subject)"}
        </h1>
        <p className="text-gray-500">
          {email.snippet}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            From
          </h3>
          <p className="text-gray-900">
            {email.sender}
          </p>
        </div>
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            To
          </h3>
          <p className="text-gray-900">
            {email.recipients.length > 0 ? email.recipients.join(", ") : "(none)"}
          </p>
        </div>
        {email.cc.length > 0 && (
          <div className="bg-gray-50 p-4 rounded-lg">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Cc
            </h3>
            <p className="text-gray-900">
              {email.cc.join(", ")}
            </p>
          </div>
        )}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-sm font-medium text-gray-500 mb-2">
            Date
          </h3>
          <p className="text-gray-900">
            {formatDate(email.received_at)}
          </p>
        </div>
      </div>

      {email.has_attachments && email.attachments.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Attachments
          </h2>
          <div className="space-y-2">
            {email.attachments.map((attachment) => (
              <div key={attachment.id} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-md">
                <div className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L18 14m-2-2l1.586-1.586a2 2 0 012.828 0L18 10m-2-2l1.586-1.586a2 2 0 012.828 0L18 6m-2-2l1.586-1.586a2 2 0 012.828 0L18 2" />
                  </svg>
                  <span className="font-medium">{attachment.filename}</span>
                </div>
                <div className="text-sm text-gray-500">
                  {attachment.mime_type} — {formatSize(attachment.size)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="pt-4 border-t border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Message
        </h2>
        <div className="prose prose-sm max-w-none text-gray-800">
          <p>{bodyText}</p>
        </div>
      </div>
    </div>
  );
}

export default EmailDetailView;