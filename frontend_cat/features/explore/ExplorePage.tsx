"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage } from "@/lib/api/client";
import {
  EMPTY_FILTERS,
  FILTER_CATEGORIES,
  exploreBanks,
  type ExploreFilters,
  type ExploreResponse,
  type FilterCategory,
} from "@/lib/api/explore";

import { EmptyState } from "./EmptyState";
import { FilterSidebar } from "./FilterSidebar";
import { LiveRatesTicker } from "./LiveRatesTicker";
import { ResultsList } from "./ResultsList";

const DEFAULT_SIDEBAR_PCT = 60;
const MIN_SIDEBAR_PCT = 25;
const MAX_SIDEBAR_PCT = 80;
const SIDEBAR_WIDTH_STORAGE_KEY = "explore-sidebar-width-pct";

export function ExplorePage() {
  const [filters, setFilters] = useState<ExploreFilters>(EMPTY_FILTERS);
  const [data, setData] = useState<ExploreResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Not sent to the backend — it doesn't affect which banks match, only
  // whether each bank's card shows a shortfall note (see ResultsList),
  // computed client-side from data the backend already returns.
  const [requestedLoanAmount, setRequestedLoanAmount] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const [sidebarPct, setSidebarPct] = useState(DEFAULT_SIDEBAR_PCT);
  const [dragging, setDragging] = useState(false);

  // AffordabilityForm keeps its own local state for the obligation rows
  // (label + amount per row) — "Clear filters" resets everything in
  // `filters`, but that alone can't touch AffordabilityForm's internal
  // state. Bumping this and passing it down as a `key` forces a full
  // remount, which is what actually clears the row inputs on screen.
  const [affordabilityResetKey, setAffordabilityResetKey] = useState(0);

  // Runs once on mount, client-side only — restores whatever width the user
  // left it at last time. Kept out of useState's initializer so the server
  // render and the first client render match (both start at the default).
  useEffect(() => {
    const saved = Number(localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
    if (saved >= MIN_SIDEBAR_PCT && saved <= MAX_SIDEBAR_PCT) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage only exists client-side, so this can't run any earlier than mount; there's no non-effect way to sync from it.
      setSidebarPct(saved);
    }
  }, []);

  const handleDividerMouseDown = useCallback(() => setDragging(true), []);

  useEffect(() => {
    if (!dragging) return;

    function handleMouseMove(e: MouseEvent) {
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSidebarPct(Math.min(MAX_SIDEBAR_PCT, Math.max(MIN_SIDEBAR_PCT, pct)));
    }
    function handleMouseUp() {
      setDragging(false);
      setSidebarPct((current) => {
        localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(current));
        return current;
      });
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging]);

  useEffect(() => {
    let cancelled = false;
    exploreBanks(filters)
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters]);

  function toggleFilter(category: FilterCategory, value: string) {
    setLoading(true);
    setFilters((prev) => {
      const current = prev[category];
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
      return { ...prev, [category]: next };
    });
  }

  function clearFilters() {
    setLoading(true);
    setFilters(EMPTY_FILTERS);
    setRequestedLoanAmount(null);
    setAffordabilityResetKey((key) => key + 1);
  }

  function setAge(value: number | null) {
    setLoading(true);
    setFilters((prev) => ({ ...prev, age: value }));
  }

  function setMonthlyIncome(value: number | null) {
    setLoading(true);
    setFilters((prev) => ({ ...prev, monthly_income: value }));
  }

  function setObligations(amounts: number[]) {
    setLoading(true);
    setFilters((prev) => ({ ...prev, obligations: amounts }));
  }

  // Only count the checkbox-style category filters here — age/income are
  // single values, not a "selection count" the same way checkboxes are.
  const activeCount = FILTER_CATEGORIES.reduce((sum, category) => sum + filters[category].length, 0);
  // Nothing picked at all yet — still fetch (the sidebar's counts need real
  // data even before a selection), but show a landing message instead of
  // dumping every bank in the database on first load.
  const hasAnyInput =
    activeCount > 0 ||
    filters.age !== null ||
    filters.monthly_income !== null ||
    filters.obligations.length > 0 ||
    requestedLoanAmount !== null;

  return (
    // h-full + each child scrolling independently (overflow-y-auto on both
    // the sidebar and the results pane) — scrolling one never moves the
    // other, same as the reference site's filter panel behaves. The sidebar
    // gets an explicit CSS-variable width so the divider between it and the
    // results can be dragged to resize both at once.
    <div className="flex h-full w-full flex-col">
      <div
        ref={containerRef}
        style={{ "--sidebar-pct": `${sidebarPct}%` } as React.CSSProperties}
        className={`flex min-h-0 w-full flex-1 flex-col sm:flex-row ${dragging ? "select-none" : ""}`}
      >
        <FilterSidebar
          filters={filters}
          facets={data?.facets ?? null}
          activeCount={activeCount}
          showClear={hasAnyInput}
          onToggle={toggleFilter}
          onClear={clearFilters}
          requestedLoanAmount={requestedLoanAmount}
          onAgeChange={setAge}
          onMonthlyIncomeChange={setMonthlyIncome}
          onObligationsChange={setObligations}
          onRequestedLoanAmountChange={setRequestedLoanAmount}
          affordabilityResetKey={affordabilityResetKey}
        />

        {/* The draggable divider — hidden below the sm breakpoint, where the
            panes stack instead of sitting side by side. */}
        <div
          onMouseDown={handleDividerMouseDown}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize filters and results"
          className={`hidden w-1.5 shrink-0 cursor-col-resize items-stretch justify-center bg-zinc-200 hover:bg-teal-400 sm:flex ${
            dragging ? "bg-teal-500" : ""
          }`}
        >
          <div className="m-auto h-10 w-0.5 rounded-full bg-zinc-400" />
        </div>

        <div className="min-h-0 w-full flex-1 overflow-y-auto px-6 py-6">
          {error ? (
            <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </p>
          ) : !hasAnyInput ? (
            <EmptyState />
          ) : (
            <ResultsList
              results={data?.results ?? []}
              total={data?.total ?? 0}
              loading={loading}
              requestedLoanAmount={requestedLoanAmount}
              onClear={clearFilters}
            />
          )}
        </div>
      </div>

      <LiveRatesTicker />
    </div>
  );
}
