import { useQuery } from "@tanstack/react-query";
import { getRecommendations } from "../api/recommendations";
import { enrichRecommendations } from "../utils/recommendations";
import { AuthMessage } from "../components/AuthMessage";

export function RecommendationsPage() {
  const query = useQuery({
    queryKey: ["recommendations"],
    queryFn: async () => getRecommendations(6),
  });

  const enriched = enrichRecommendations(query.data?.data ?? []);

  return (
    <section className="page-section">
      <div className="section-header">
        <h1>Recommended for you</h1>
        <p>Routes shaped by your travel history and preferences.</p>
      </div>
      {query.isLoading ? <div className="skeleton-list"><div className="skeleton-card" /></div> : null}
      {query.isError ? <AuthMessage variant="error">We could not load recommendations right now. Please try again shortly.</AuthMessage> : null}
      {!query.isLoading && !query.isError && enriched.length === 0 ? <AuthMessage variant="info">No recommendations are available yet. Start searching to unlock tailored suggestions.</AuthMessage> : null}
      <div className="grid">
        {enriched.map((item, index) => (
          <article className="card-panel" key={`${item.origin}-${item.destination}-${index}`}>
            <div className="eyebrow">{item.budgetTier} · {item.season}</div>
            <h3>{item.origin} → {item.destination}</h3>
            <b>{item.currency} {item.estimated_price.toFixed(2)}</b>
            <p>{item.reason}</p>
            <div className="meta-row compact">
              {item.highlights?.map((highlight) => <span className="pill" key={highlight}>{highlight}</span>)}
            </div>
            <p className="result-subtitle">Similarity score {item.similarityScore}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
