"use client";

import { create } from "zustand";
import type { OperatorUser, TokenPair } from "@/lib/api";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: OperatorUser | null;
  setTokens: (tokens: TokenPair) => void;
  setUser: (user: OperatorUser | null) => void;
  hydrate: () => void;
  clear: () => void;
};

const ACCESS_KEY = "operator.access";
const REFRESH_KEY = "operator.refresh";

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  setTokens: (tokens) => {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },
  setUser: (user) => set({ user }),
  hydrate: () => {
    set({
      accessToken: localStorage.getItem(ACCESS_KEY),
      refreshToken: localStorage.getItem(REFRESH_KEY)
    });
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    set({ accessToken: null, refreshToken: null, user: null });
  }
}));

