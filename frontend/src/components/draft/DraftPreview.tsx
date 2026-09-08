import type { Draft } from "@/types";

interface DraftPreviewProps {
  draft: Draft;
}

function DraftPreview({ draft }: DraftPreviewProps) {
  return (
    <section>
      <h2>Generated Draft</h2>
      <p style={{ whiteSpace: "pre-wrap" }}>{draft.body}</p>
    </section>
  );
}

export default DraftPreview;