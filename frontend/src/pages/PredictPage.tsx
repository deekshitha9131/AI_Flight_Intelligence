import { FormEvent, useMemo } from "react";
import { usePrediction } from "../hooks/usePrediction";
import { getConfidenceLabel, getPredictionErrorMessage } from "../hooks/predictionUtils";
import type { ToastType } from "../types";

export function PredictPage({ today, onNotify }: { today: string; onNotify: (message: string, type?: ToastType) => void }) {
  const { mutation, submitPrediction } = usePrediction(onNotify);
  const confidenceLabel = useMemo(() => getConfidenceLabel(mutation.data?.data.confidence_score), [mutation.data?.data.confidence_score]);
  const errorMessage = getPredictionErrorMessage(mutation.error);

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>AI price prediction</h1>
        <p>Estimate fare movement before you finalize your itinerary.</p>
      </div>
      <form
        className="predict"
        onSubmit={(event: FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          submitPrediction(event.currentTarget);
        }}
      >
        <label className="field">
          Origin
          <input name="origin" defaultValue="HYD" maxLength={3} />
        </label>
        <label className="field">
          Destination
          <input name="destination" defaultValue="DXB" maxLength={3} />
        </label>
        <label className="field">
          Departure
          <input name="departure_date" type="date" min={today} defaultValue={today} />
        </label>
        <label className="field">
          Adults
          <input name="adults" type="number" min="1" defaultValue="1" />
        </label>
        <button className="primary-button" type="submit">
          Forecast fare
        </button>
      </form>
      {mutation.isPending ? <div className="skeleton-list"><div className="skeleton-card" /></div> : null}
      {mutation.isError ? <div className="message error">{errorMessage ?? "We could not generate a price estimate right now. Please try again."}</div> : null}
      {mutation.data ? (
        <article className="forecast card-panel">
          <p className="eyebrow">Likely fare</p>
          <h2>
            {mutation.data.data.currency} {mutation.data.data.predicted_price.toFixed(2)}
          </h2>
          <p>{confidenceLabel} · {Math.round((mutation.data.data.confidence_score ?? 0) * 100)}% confidence</p>
          <p>Range: {mutation.data.data.price_range_low}–{mutation.data.data.price_range_high}</p>
          <p>{mutation.data.data.suggested_booking_window ?? "Book once the fare is within your comfort range."}</p>
          <div className="meta-row compact">
            <span className="pill">{mutation.data.data.predicted_price < mutation.data.data.price_range_high ? "Buy soon" : "Wait"}</span>
            <span className="pill">Historical trend: stable</span>
            <span className="pill">Best booking window: {mutation.data.data.suggested_booking_window ?? "soon"}</span>
          </div>
        </article>
      ) : null}
    </section>
  );
}
