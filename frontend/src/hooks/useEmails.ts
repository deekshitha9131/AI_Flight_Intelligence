import { useCallback, useEffect, useState } from "react";

import { listEmails, type ListEmailsParams } from "@/api/emails";
import type { EmailSummary } from "@/types";

type Status = "loading" | "success" | "error";

interface UseEmailsResult {
  status: Status;
  emails: EmailSummary[];
  page: number;
  pageSize: number;
  total: number;
  isEmpty: boolean;
  errorMessage: string | null;
  setPage: (page: number) => void;
  retry: () => void;
}

const PAGE_SIZE = 25;

export function useEmails(params: Omit<ListEmailsParams, "page" | "page_size"> = {}): UseEmailsResult {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<Status>("loading");
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const fetchEmails = useCallback(async () => {
    setStatus("loading");
    setErrorMessage(null);
    try {
      const result = await listEmails({ ...params, page, page_size: PAGE_SIZE });
      setEmails(result.items);
      setTotal(result.total);
      setStatus("success");
    } catch {
      setErrorMessage("We couldn't load your inbox. Please try again.");
      setStatus("error");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, reloadToken]);

  useEffect(() => {
    void fetchEmails();
  }, [fetchEmails]);

  const retry = useCallback(() => setReloadToken((token) => token + 1), []);

  return {
    status,
    emails,
    page,
    pageSize: PAGE_SIZE,
    total,
    isEmpty: status === "success" && emails.length === 0,
    errorMessage,
    setPage,
    retry,
  };
}