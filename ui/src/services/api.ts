/**
 * API service for chat endpoint communication.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  context?: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  metadata?: {
    intent?: string;
    skill?: string;
    latency_ms?: number;
    routing_source?: string;
  };
}

export interface ErrorResponse {
  error: string;
  code: number;
}

/**
 * Send a chat message to the backend API.
 */
export async function sendChat(
  request: ChatRequest
): Promise<ChatResponse | ErrorResponse> {
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        error: data.error || "An error occurred",
        code: response.status,
      };
    }

    return data as ChatResponse;
  } catch (error) {
    return {
      error: `Failed to connect to chat service: ${String(error)}`,
      code: 500,
    };
  }
}

/**
 * Check if response is an error.
 */
export function isError(
  response: ChatResponse | ErrorResponse
): response is ErrorResponse {
  return "code" in response && "error" in response;
}
