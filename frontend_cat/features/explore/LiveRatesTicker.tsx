"use client";

import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api/client";
import { fetchLiveRates, type LiveRate } from "@/lib/api/explore";

// Scrolling footer bar showing every bank rate that's actually been
// confirmed against Ambak (see the live-rates endpoint) — never the
// "Interest rate not verified" banks, since this is meant to read as real,
// current data, not a placeholder. Refetches periodically so it reflects
// whatever the daily Ambak scrape currently has, without needing a reload.
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

function RateChip({ rate }: { rate: LiveRate }) {
  return (
    <span className="mx-3 inline-flex shrink-0 items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-sm font-semibold text-white">
      {rate.bank_name}
      <span className="font-black text-teal-300">{rate.rate_pct.toFixed(2)}%</span>
    </span>
  );
}

export function LiveRatesTicker() {
  const [rates, setRates] = useState<LiveRate[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    function load() {
      fetchLiveRates()
        .then((data) => {
          if (!cancelled) {
            setRates(data);
            setError(null);
          }
        })
        .catch((err) => {
          if (!cancelled) setError(errorMessage(err));
        });
    }

    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Nothing confirmed yet (still loading, request failed, or every bank is
  // currently unverified) — no ticker rather than an empty/broken-looking bar.
  if (!rates || rates.length === 0 || error) return null;

  return (
    <div className="flex shrink-0 items-center gap-3 overflow-hidden border-t-2 border-zinc-900 bg-zinc-900 py-2.5 dark:border-teal-500">
      <div className="flex shrink-0 items-center gap-1.5 pl-4 pr-3">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
        </span>
        <span className="text-xs font-black uppercase tracking-widest text-white">Live rates</span>
      </div>
      <div className="group relative flex-1 overflow-hidden">
        <div
          className="flex w-max items-center [animation:ticker-scroll_50s_linear_infinite] group-hover:[animation-play-state:paused]"
          style={{ animationDuration: `${Math.max(rates.length * 3, 25)}s` }}
        >
          {/* Rendered twice back-to-back so the -50% loop point is seamless. */}
          {[...rates, ...rates].map((rate, i) => (
            <RateChip key={`${rate.bank_name}-${i}`} rate={rate} />
          ))}
        </div>
      </div>
    </div>
  );
}
