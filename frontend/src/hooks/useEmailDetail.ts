import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/api/client";
import { getEmail } from "@/api/emails";
import type { EmailDetail } from "@/types";

type Status = "loading" | "success" | "not_found" | "error";

interface UseEmailDetailResult {
  status: Status;
  email: EmailDetail | null;
  retry: () => void;
}

export function useEmailDetail(emailId: string): UseEmailDetailResult {
  const [status, setStatus] = useState<Status>("loading");
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const fetchEmail = useCallback(async () => {
    setStatus("loading");
    try {
      const result = await getEmail(emailId);
      setEmail(result);
      setStatus("success");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setStatus("not_found");
      } else {
        setStatus("error");
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [emailId, reloadToken]);

  useEffect(() => {
    void fetchEmail();
  }, [fetchEmail]);

  const retry = useCallback(() => setReloadToken((token) => token + 1), []);

  return { status, email, retry };
}