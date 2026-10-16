import { useQuery } from "@tanstack/react-query";
import { api, authConfig, type Account, type Category, type User } from "./api";

export const useMe = () => useQuery({ queryKey: ["me"], queryFn: () => api<User>("/auth/me"), retry: false });
export const useCategories = () => useQuery({ queryKey: ["categories"], queryFn: () => api<Category[]>("/categories") });
export const useAccounts = () => useQuery({ queryKey: ["accounts"], queryFn: () => api<Account[]>("/accounts") });
export const useAiEnabled = () => useQuery({ queryKey: ["auth-config"], queryFn: authConfig, staleTime: Infinity, retry: 1 }).data?.ai_enabled ?? false;
