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
        {enriched.map((item, index) => {
          const tierLabel = item.budgetTier ? item.budgetTier.charAt(0).toUpperCase() + item.budgetTier.slice(1) : "Value";
          const seasonLabel = item.season ? item.season.charAt(0).toUpperCase() + item.season.slice(1) : "Spring";

          return (
            <article className="card-panel" key={`${item.origin}-${item.destination}-${index}`} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <div className="eyebrow" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span>{tierLabel} Option</span>
                <span className="pill" style={{ textTransform: "capitalize" }}>{seasonLabel} Window</span>
              </div>
              <h3 style={{ margin: "0.2rem 0" }}>{item.origin} → {item.destination}</h3>
              <b style={{ fontSize: "1.1rem", color: "var(--primary)" }}>{item.currency} {item.estimated_price.toFixed(2)}</b>
              
              <div style={{ margin: "0.4rem 0" }}>
                <small style={{ display: "block", color: "var(--muted)", fontWeight: 600 }}>Why this recommendation:</small>
                <p style={{ margin: "0.2rem 0" }}>{item.reason}</p>
              </div>

              <div className="meta-row compact" style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginTop: "auto" }}>
                {item.highlights?.map((highlight) => (
                  <span className="pill" key={highlight} style={{ fontSize: "0.8rem", padding: "0.2rem 0.5rem" }}>
                    {highlight}
                  </span>
                ))}
              </div>
              <p className="result-subtitle" style={{ margin: 0, fontSize: "0.75rem", color: "var(--muted)" }}>
                Match score: {(item.similarityScore ?? 0.85) * 100}%
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
