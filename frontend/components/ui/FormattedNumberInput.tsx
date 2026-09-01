"use client";

interface FormattedNumberInputProps {
  id: string;
  placeholder: string;
  value: number | undefined;
  onChange: (value: number | undefined) => void;
}

export function FormattedNumberInput({ id, placeholder, value, onChange }: FormattedNumberInputProps) {
  const displayValue = value === undefined || Number.isNaN(value) ? "" : value.toLocaleString("en-IN");

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const digitsOnly = e.target.value.replace(/[^0-9]/g, "");
    onChange(digitsOnly === "" ? undefined : Number(digitsOnly));
  }

  return (
    <input
      id={id}
      type="text"
      inputMode="numeric"
      placeholder={placeholder}
      value={displayValue}
      onChange={handleChange}
      className="rounded-lg border border-zinc-200 bg-white/80 px-4 py-2.5 text-base outline-none focus:border-teal-500 dark:border-zinc-700 dark:bg-zinc-950"
    />
  );
}
