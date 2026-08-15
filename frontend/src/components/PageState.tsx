import { Loader2 } from "lucide-react";

type PageStateProps = {
  title: string;
  description?: string;
  action?: React.ReactNode;
  variant?: "empty" | "error" | "loading";
};

export function PageState({ title, description, action, variant = "empty" }: PageStateProps) {
  if (variant === "loading") {
    return (
      <div className="empty-state" data-testid="page-loading">
        <div className="empty-icon"><Loader2 size={32} className="spin" /></div>
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
        {action ? <div>{action}</div> : null}
      </div>
    );
  }

  return (
    <div className="empty-state" data-testid={`page-${variant}`}>
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
      {action ? <div>{action}</div> : null}
    </div>
  );
}
