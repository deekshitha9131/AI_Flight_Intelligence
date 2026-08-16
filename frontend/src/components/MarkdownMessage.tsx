import React from "react";

interface MarkdownMessageProps {
  content: string;
}

function parseInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.*?)\*\*/);
    const italicMatch = remaining.match(/\*(.*?)\*/);
    const codeMatch = remaining.match(/`(.*?)`/);

    let firstMatch: { type: "bold" | "italic" | "code"; index: number; length: number; content: string } | null = null;

    if (boldMatch && boldMatch.index !== undefined) {
      firstMatch = { type: "bold", index: boldMatch.index, length: boldMatch[0].length, content: boldMatch[1] };
    }
    if (italicMatch && italicMatch.index !== undefined) {
      if (!firstMatch || italicMatch.index < firstMatch.index) {
        firstMatch = { type: "italic", index: italicMatch.index, length: italicMatch[0].length, content: italicMatch[1] };
      }
    }
    if (codeMatch && codeMatch.index !== undefined) {
      if (!firstMatch || codeMatch.index < firstMatch.index) {
        firstMatch = { type: "code", index: codeMatch.index, length: codeMatch[0].length, content: codeMatch[1] };
      }
    }

    if (!firstMatch) {
      parts.push(remaining);
      break;
    }

    if (firstMatch.index > 0) {
      parts.push(remaining.substring(0, firstMatch.index));
    }

    if (firstMatch.type === "bold") {
      parts.push(<strong key={keyIdx++}>{parseInline(firstMatch.content)}</strong>);
    } else if (firstMatch.type === "italic") {
      parts.push(<em key={keyIdx++}>{firstMatch.content}</em>);
    } else if (firstMatch.type === "code") {
      parts.push(<code key={keyIdx++}>{firstMatch.content}</code>);
    }

    remaining = remaining.substring(firstMatch.index + firstMatch.length);
  }

  return parts;
}

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  let inList: "ul" | "ol" | null = null;
  let listItems: React.ReactNode[] = [];
  let inTable = false;
  let tableHeader: string[] = [];
  let tableRows: string[][] = [];

  const flushList = () => {
    if (inList && listItems.length > 0) {
      if (inList === "ul") {
        elements.push(<ul key={`ul-${elements.length}`}>{listItems}</ul>);
      } else {
        elements.push(<ol key={`ol-${elements.length}`}>{listItems}</ol>);
      }
      listItems = [];
      inList = null;
    }
  };

  const flushTable = () => {
    if (inTable) {
      elements.push(
        <div key={`table-wrap-${elements.length}`} className="table-responsive" style={{ margin: "12px 0", overflowX: "auto" }}>
          <table className="markdown-table" style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            {tableHeader.length > 0 && (
              <thead>
                <tr style={{ borderBottom: "2px solid rgba(255,255,255,0.15)" }}>
                  {tableHeader.map((h, i) => (
                    <th key={i} style={{ padding: "6px 12px" }}>{parseInline(h)}</th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {tableRows.map((row, rIdx) => (
                <tr key={rIdx} style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: "6px 12px" }}>{parseInline(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      inTable = false;
      tableHeader = [];
      tableRows = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      flushTable();
      continue;
    }

    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList();
      const cells = trimmed
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());

      if (cells.every((c) => /^:?-+:?$/.test(c))) {
        continue;
      }

      if (!inTable) {
        inTable = true;
        tableHeader = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    } else {
      flushTable();
    }

    if (trimmed.startsWith("### ")) {
      flushList();
      elements.push(<h3 key={`h3-${i}`} style={{ marginTop: "14px", marginBottom: "6px" }}>{parseInline(trimmed.substring(4))}</h3>);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      flushList();
      elements.push(<h2 key={`h2-${i}`} style={{ marginTop: "16px", marginBottom: "8px" }}>{parseInline(trimmed.substring(3))}</h2>);
      continue;
    }
    if (trimmed.startsWith("# ")) {
      flushList();
      elements.push(<h1 key={`h1-${i}`} style={{ marginTop: "18px", marginBottom: "10px" }}>{parseInline(trimmed.substring(2))}</h1>);
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (inList !== "ul") {
        flushList();
        inList = "ul";
      }
      listItems.push(<li key={`li-${i}`}>{parseInline(trimmed.substring(2))}</li>);
      continue;
    }

    const olMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (olMatch) {
      if (inList !== "ol") {
        flushList();
        inList = "ol";
      }
      listItems.push(<li key={`li-${i}`}>{parseInline(olMatch[2])}</li>);
      continue;
    }

    flushList();
    elements.push(<p key={`p-${i}`} style={{ marginBottom: "8px" }}>{parseInline(trimmed)}</p>);
  }

  flushList();
  flushTable();

  return <div className="markdown-content">{elements}</div>;
}
