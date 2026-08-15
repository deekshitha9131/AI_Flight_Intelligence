import { Sparkles } from "lucide-react";
import { SearchForm } from "../components/SearchForm";
import type { AirportOption, ToastType } from "../types";

export type HomePageProps = {
  airportOptions: AirportOption[];
  today: string;
  onNotify: (message: string, type?: ToastType) => void;
};

export function HomePage({ airportOptions, today, onNotify }: HomePageProps) {
  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><Sparkles size={16} /> Predict. Compare. Fly smarter.</p>
          <h1>Every journey starts with a better fare.</h1>
          <p>Search modern routes, compare polished offers, and let the assistant help with the details.</p>
          <SearchForm onNotify={onNotify} today={today} airportOptions={airportOptions} />
          <div className="stats">
            <span>AI price forecasts</span>
            <span>Personalised trips</span>
            <span>24/7 travel assistant</span>
          </div>
        </div>
      </section>
      <section className="page-section">
        <div className="section-header">
          <h2>Designed around your next destination</h2>
        </div>
        <div className="grid">
          <article className="card-panel"><h3>Price prediction</h3><small>Know the likely fare before you book.</small></article>
          <article className="card-panel"><h3>Smart recommendations</h3><small>Routes shaped by your history and budget.</small></article>
          <article className="card-panel"><h3>Travel assistant</h3><small>Helpful guidance whenever you need it.</small></article>
        </div>
      </section>
    </>
  );
}
