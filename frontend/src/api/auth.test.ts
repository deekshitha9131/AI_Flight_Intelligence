import { describe, it, expect, vi, beforeEach } from "vitest";
import { login } from "./auth";
import client from "./client";

vi.mock("./client", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("auth api", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns tokens and user after login", async () => {
    vi.mocked(client.post).mockResolvedValueOnce({ data: { data: { access_token: "a", refresh_token: "r", token_type: "bearer", expires_in: 3600 } } } as never);
    vi.mocked(client.get).mockResolvedValueOnce({ data: { data: { id: "1", first_name: "A", last_name: "B", email: "a@test.com" } } } as never);

    const result = await login({ email: "a@test.com", password: "secret" });
    expect(result.tokens.access_token).toBe("a");
    expect(result.user.email).toBe("a@test.com");
  });
});
