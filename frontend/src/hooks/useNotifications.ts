import { useEffect, useState } from "react";
import type { ToastItem, ToastType } from "../types";

export function useNotifications() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    return () => {
      setToasts([]);
    };
  }, []);

  const pushToast = (message: string, type: ToastType = "info") => {
    const timer = window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== timer));
    }, 3000);
    setToasts((current) => [...current, { id: timer, type, message }]);
  };

  return { toasts, pushToast };
}
