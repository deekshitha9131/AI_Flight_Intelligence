import { FormEvent, useMemo } from "react";
import { usePrediction } from "../hooks/usePrediction";
import { getConfidenceLabel, getPredictionErrorMessage } from "../hooks/predictionUtils";
import type { ToastType } from "../types";

export function PredictPage({ today, onNotify }: { today: string; onNotify: (message: string, type?: ToastType) => void }) {
  const { mutation, submitPrediction } = usePrediction(onNotify);
  const confidenceLabel = useMemo(
    () => getConfidenceLabel(mutation.data?.data.confidence_score),
    [mutation.data?.data.confidence_score]
  );
  const errorMessage = getPredictionErrorMessage(mutation.error);

  const predData = mutation.data?.data;
  const isBuySoon = predData ? predData.predicted_price < predData.price_range_high : true;

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

      {mutation.isPending ? (
        <div className="skeleton-list">
          <div className="skeleton-card" />
        </div>
      ) : null}

      {mutation.isError ? (
        <div className="message error">
          {errorMessage ?? "We could not generate a price estimate right now. Please try again."}
        </div>
      ) : null}

      {predData ? (
        <article className="forecast card-panel">
          <div className="forecast-header">
            <span className="eyebrow">Likely fare</span>
            <div className="price-primary">
              {predData.currency} {predData.predicted_price.toFixed(2)}
            </div>
            <div className="forecast-sub">
              {confidenceLabel} · {Math.round((predData.confidence_score ?? 0) * 100)}% confidence
            </div>
          </div>

          <div className="forecast-grid">
            <div className="forecast-item">
              <span className="forecast-label">Recommendation</span>
              <strong className={`forecast-value ${isBuySoon ? "accent" : ""}`}>
                {isBuySoon ? "Buy soon" : "Wait"}
              </strong>
            </div>

            <div className="forecast-item">
              <span className="forecast-label">Historical Trend</span>
              <strong className="forecast-value">Stable</strong>
            </div>

            <div className="forecast-item">
              <span className="forecast-label">Price Range</span>
              <strong className="forecast-value">
                {predData.currency} {predData.price_range_low.toFixed(2)} – {predData.currency} {predData.price_range_high.toFixed(2)}
              </strong>
            </div>

            <div className="forecast-item">
              <span className="forecast-label">Best Booking Window</span>
              <strong className="forecast-value">
                {predData.suggested_booking_window ?? "Book 14–21 days in advance"}
              </strong>
            </div>
          </div>
        </article>
      ) : null}
    </section>
  );
}
