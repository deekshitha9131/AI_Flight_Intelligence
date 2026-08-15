import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { Header } from "./Header";
import { useAuthStore } from "../store/auth";

describe("Header", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, tokens: null, isHydrated: true });
  });

  it("renders the brand and toggles the theme callback", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Header theme="light" onToggleTheme={() => {}} onNotify={() => {}} />
      </MemoryRouter>,
    );

    expect(screen.getByText("AI Flight")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /switch to dark theme/i }));
  });
});
