import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  it("submits the login form", async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <LoginPage onNotify={() => {}} />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.type(screen.getByLabelText(/email/i), "demo@example.com");
    await user.type(screen.getByPlaceholderText(/enter your password/i), "Password123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
  });
});
