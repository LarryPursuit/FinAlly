"use client";

import { useEffect, useRef, useState } from "react";

type FlashDirection = "up" | "down" | null;

export function usePriceFlash(price: number | null | undefined): string {
  const prevPrice = useRef(price);
  const [flash, setFlash] = useState<FlashDirection>(null);

  useEffect(() => {
    if (price == null || prevPrice.current == null) {
      prevPrice.current = price;
      return;
    }

    if (price > prevPrice.current) {
      setFlash("up");
    } else if (price < prevPrice.current) {
      setFlash("down");
    }

    prevPrice.current = price;

    const timer = setTimeout(() => setFlash(null), 500);
    return () => clearTimeout(timer);
  }, [price]);

  if (flash === "up") return "price-flash-up";
  if (flash === "down") return "price-flash-down";
  return "";
}
