import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownMessage } from "./MarkdownMessage";

describe("MarkdownMessage", () => {
  it("renders headings, bold, bullet points, and tables correctly", () => {
    const markdown = `
### Flight Search
**Best option**
- Air India
- Emirates

| Airline | Flight | Price |
| --- | --- | --- |
| IndiGo | 6E201 | $321.00 |
`;

    render(<MarkdownMessage content={markdown} />);

    expect(screen.getByRole("heading", { level: 3, name: "Flight Search" })).toBeInTheDocument();
    expect(screen.getByText("Best option")).toBeInTheDocument();
    expect(screen.getByText("Air India")).toBeInTheDocument();
    expect(screen.getByText("Emirates")).toBeInTheDocument();
    expect(screen.getByText("IndiGo")).toBeInTheDocument();
    expect(screen.getByText("6E201")).toBeInTheDocument();
  });
});
