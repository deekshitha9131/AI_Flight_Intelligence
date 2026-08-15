import { useMutation } from "@tanstack/react-query";
import { predictPrice } from "../api/prediction";
import type { ToastType } from "../types";
import { getPredictionErrorMessage } from "./predictionUtils";

export function usePrediction(onNotify?: (message: string, type?: ToastType) => void) {
  const mutation = useMutation({
    mutationFn: async (values: Record<string, unknown>) => predictPrice(values),
    onSuccess: () => onNotify?.("Prediction completed.", "success"),
    onError: (error) => onNotify?.(getPredictionErrorMessage(error) ?? "We could not generate a price estimate right now.", "error"),
  });

  const submitPrediction = (form: HTMLFormElement) => {
    const formData = Object.fromEntries(new FormData(form));
    mutation.mutate({
      ...formData,
      adults: Number(formData.adults ?? 1),
      children: Number(formData.children ?? 0),
      infants: Number(formData.infants ?? 0),
      stops: formData.stops ? Number(formData.stops) : null,
      duration_minutes: formData.duration_minutes ? Number(formData.duration_minutes) : null,
    });
  };

  return { mutation, submitPrediction };
}
