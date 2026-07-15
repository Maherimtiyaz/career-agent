import api from "./api";
import type { Token, User } from "@/types";

export async function login(email: string, password: string): Promise<Token> {
  const res = await api.post<Token>("/auth/login", { email, password });
  localStorage.setItem("access_token", res.data.access_token);
  localStorage.setItem("refresh_token", res.data.refresh_token);
  return res.data;
}

export async function register(email: string, password: string, full_name?: string): Promise<User> {
  const res = await api.post<User>("/auth/register", { email, password, full_name });
  return res.data;
}

export function logout(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

export async function getMe(): Promise<User> {
  const res = await api.get<User>("/auth/me");
  return res.data;
}
