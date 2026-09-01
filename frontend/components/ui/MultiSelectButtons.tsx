"use client";

interface Option {
  value: string;
  label: string;
}

interface MultiSelectButtonsProps {
  options: readonly Option[];
  values: string[];
  onChange: (values: string[]) => void;
  name: string;
  requiredValue?: string;
}

export function MultiSelectButtons({ options, values, onChange, name, requiredValue }: MultiSelectButtonsProps) {
  function toggle(value: string) {
    if (values.includes(value)) {
      onChange(values.filter((v) => v !== value));
    } else {
      onChange([...values, value]);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2" role="group" aria-label={name}>
      {options.map((option) => {
        const selected = values.includes(option.value);
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            onClick={() => toggle(option.value)}
            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left text-base font-medium transition-colors ${
              selected
                ? "border-teal-500 bg-teal-50 text-teal-900 dark:border-teal-500 dark:bg-teal-950/40 dark:text-teal-100"
                : "border-zinc-200 bg-white text-zinc-700 hover:border-teal-300 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
            }`}
          >
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                selected
                  ? "border-teal-600 bg-teal-600"
                  : "border-zinc-300 bg-white dark:border-zinc-600 dark:bg-zinc-800"
              }`}
            >
              {selected && (
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </span>
            <span className="flex-1">{option.label}</span>
            {option.value === requiredValue && (
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  selected
                    ? "bg-teal-600 text-white"
                    : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                }`}
              >
                Required
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
