const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// The backend's error body is JSON like {"detail": "..."} — this pulls out
// that plain-English detail instead of showing the raw JSON to the user.
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.message);
      if (parsed && typeof parsed.detail === "string") return parsed.detail;
    } catch {
      // not JSON — fall through to the raw message below
    }
    return err.message;
  }
  return "Something went wrong. Check the backend is running and try again.";
}

export async function apiPost<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status);
  }

  return response.json() as Promise<TResponse>;
}
