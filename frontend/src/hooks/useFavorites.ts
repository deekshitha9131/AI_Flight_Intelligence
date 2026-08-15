import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getFavorites, removeFavorite as removeFavoriteRequest, saveFavorite as saveFavoriteRequest } from "../api/flights";
import type { ToastType } from "../types";
import type { FavoriteItem, FavoriteListResponse, FavoritePayload } from "../api/flights";
import { mergeFavoriteItem, removeFavoriteItem } from "./favoritesUtils";

import { useAuthStore } from "../store/auth";

function getErrorMessage(error: unknown): string | undefined {
  const responseData = (error as { response?: { data?: { message?: string; detail?: string; error?: string } } }).response?.data;
  return responseData?.message || responseData?.detail || responseData?.error;
}

export function useFavorites(onNotify?: (message: string, type?: ToastType) => void) {
  const queryClient = useQueryClient();
  const tokens = useAuthStore((s) => s.tokens);
  const [filter, setFilter] = useState("");
  const [sortBy, setSortBy] = useState<"recent" | "price" | "route">("recent");

  const favoritesQuery = useQuery({
    queryKey: ["favorites"],
    queryFn: async () => getFavorites(1, 50),
    enabled: Boolean(tokens),
  });


  const removeFavorite = useMutation({
    mutationFn: async (id: string) => removeFavoriteRequest(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["favorites"] });
      const previous = queryClient.getQueryData<FavoriteListResponse>(["favorites"]);
      if (previous) {
        queryClient.setQueryData(["favorites"], removeFavoriteItem(previous, id));
      }
      return { previous };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      onNotify?.("Favorite removed.", "success");
    },
    onError: (error, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["favorites"], context.previous);
      }
      onNotify?.(getErrorMessage(error) ?? "Unable to remove that favorite right now.", "error");
    },
  });

  const saveFavorite = useMutation({
    mutationFn: async (payload: FavoritePayload) => {
      const response = await saveFavoriteRequest(payload);
      return response.data.data as FavoriteItem;
    },
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ["favorites"] });
      const previous = queryClient.getQueryData<FavoriteListResponse>(["favorites"]);
      const optimisticItem: FavoriteItem = {
        id: `${payload.flight_offer_id}-${Date.now()}`,
        flight_offer_id: payload.flight_offer_id,
        airline: payload.airline,
        origin: payload.origin,
        destination: payload.destination,
        departure: payload.departure,
        arrival: payload.arrival,
        price: payload.price,
        currency: payload.currency,
        created_at: new Date().toISOString(),
      };
      if (previous) {
        queryClient.setQueryData(["favorites"], mergeFavoriteItem(previous, optimisticItem));
      }
      return { previous };
    },
    onSuccess: (item) => {
      queryClient.setQueryData(["favorites"], (current: FavoriteListResponse | undefined) => mergeFavoriteItem(current, item));
      queryClient.invalidateQueries({ queryKey: ["favorites"] });
      onNotify?.("Saved to your favorites list.", "success");
    },
    onError: (error, _payload, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["favorites"], context.previous);
      }
      onNotify?.(getErrorMessage(error) ?? "That trip is already in your favorites.", "warning");
    },
  });

  const filteredFavorites = useMemo(() => {
    const items = Array.isArray(favoritesQuery.data?.data) ? favoritesQuery.data.data : [];
    const search = filter.trim().toLowerCase();
    const filtered = search
      ? items.filter((item) => `${item.airline} ${item.origin} ${item.destination}`.toLowerCase().includes(search))
      : items;

    return [...filtered].sort((left, right) => {
      if (sortBy === "price") return left.price - right.price;
      if (sortBy === "route") return `${left.origin}${left.destination}`.localeCompare(`${right.origin}${right.destination}`);
      return right.departure.localeCompare(left.departure);
    });
  }, [favoritesQuery.data?.data, filter, sortBy]);

  const favoriteIds = useMemo(() => new Set((Array.isArray(favoritesQuery.data?.data) ? favoritesQuery.data.data : []).map((item) => item.flight_offer_id)), [favoritesQuery.data?.data]);

  const isFavorite = (flightId: string) => favoriteIds.has(flightId);

  return {
    favoritesQuery,
    removeFavorite,
    saveFavorite,
    filter,
    setFilter,
    sortBy,
    setSortBy,
    filteredFavorites,
    isFavorite,
  };
}
