import type { FavoriteItem, FavoriteListResponse } from "../api/flights";

export function mergeFavoriteItem(current: FavoriteListResponse | undefined, item: FavoriteItem) {
  if (!current) {
    return { success: true, message: "ok", data: [item], count: 1 } satisfies FavoriteListResponse;
  }

  const nextItems = [item, ...current.data.filter((entry) => entry.id !== item.id && entry.flight_offer_id !== item.flight_offer_id)];
  return {
    ...current,
    data: nextItems,
    count: nextItems.length,
  } satisfies FavoriteListResponse;
}

export function removeFavoriteItem(current: FavoriteListResponse | undefined, id: string) {
  if (!current) {
    return undefined;
  }

  const nextItems = current.data.filter((entry) => entry.id !== id);
  return {
    ...current,
    data: nextItems,
    count: nextItems.length,
  } satisfies FavoriteListResponse;
}
