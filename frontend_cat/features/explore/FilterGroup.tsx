"use client";

import type { FacetOption } from "@/lib/api/explore";

interface FilterGroupProps {
  title: string;
  options: FacetOption[];
  selected: string[];
  onToggle: (value: string) => void;
  // Optional: render options under sub-headings instead of one flat list —
  // used for Property Type, which has 14 values across 4 classifications.
  subgroups?: { heading: string; values: string[] }[];
}

function OptionRow({
  option,
  checked,
  onToggle,
}: {
  option: FacetOption;
  checked: boolean;
  onToggle: (value: string) => void;
}) {
  const disabled = option.count === 0 && !checked;
  return (
    <label
      className={`flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-2.5 text-base transition-colors ${
        checked
          ? "bg-teal-50 dark:bg-teal-950/40"
          : disabled
            ? "cursor-not-allowed opacity-40"
            : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
      }`}
    >
      <span className="flex items-center gap-2.5">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={() => onToggle(option.value)}
          className="h-5 w-5 rounded border-zinc-400 text-teal-600 focus:ring-2 focus:ring-teal-500 dark:border-zinc-600"
        />
        <span className={`font-semibold ${checked ? "text-teal-900 dark:text-teal-200" : "text-zinc-800 dark:text-zinc-200"}`}>
          {option.label}
        </span>
      </span>
      <span
        className={`min-w-[1.75rem] rounded-full px-1.5 py-0.5 text-center text-xs font-bold ${
          checked
            ? "bg-teal-600 text-white"
            : option.count === 0
              ? "text-zinc-300 dark:text-zinc-600"
              : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
        }`}
      >
        {option.count}
      </span>
    </label>
  );
}

export function FilterGroup({ title, options, selected, onToggle, subgroups }: FilterGroupProps) {
  const byValue = new Map(options.map((o) => [o.value, o]));

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="mb-3 border-l-4 border-teal-600 pl-2.5 text-base font-black uppercase tracking-wide text-zinc-900 dark:text-zinc-50">
        {title}
      </h3>
      {subgroups ? (
        <div className="flex flex-col gap-3">
          {subgroups.map((group) => {
            // No bank in the loaded data accepts anything in this
            // sub-group (e.g. Industrial), so there's nothing to check —
            // skip the heading entirely rather than showing an empty one.
            const availableValues = group.values.filter((value) => byValue.has(value));
            if (availableValues.length === 0) return null;
            return (
              <div key={group.heading}>
                <p className="mb-1 px-2 text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                  {group.heading}
                </p>
                <div className="flex flex-col">
                  {availableValues.map((value) => (
                    <OptionRow
                      key={value}
                      option={byValue.get(value)!}
                      checked={selected.includes(value)}
                      onToggle={onToggle}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col">
          {options.map((option) => (
            <OptionRow
              key={option.value}
              option={option}
              checked={selected.includes(option.value)}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}
