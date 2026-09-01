"use client";

import type { ReactNode } from "react";

interface Option {
  value: string;
  label: string;
}

interface ButtonGroupProps {
  options: readonly Option[];
  value: string | undefined;
  onChange: (value: string) => void;
  name: string;
  // Optional icon per option value — purely cosmetic, falls back to no icon
  // if a value isn't in the map.
  icons?: Record<string, ReactNode>;
}

export function ButtonGroup({ options, value, onChange, name, icons }: ButtonGroupProps) {
  return (
    <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={name}>
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`flex flex-1 basis-[45%] items-center justify-center gap-2 rounded-xl border px-5 py-2.5 text-base font-medium transition-colors sm:basis-0 ${
              selected
                ? "border-teal-600 bg-teal-600 text-white"
                : "border-zinc-200 bg-white text-zinc-700 hover:border-teal-300 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
            }`}
          >
            {icons?.[option.value]}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
