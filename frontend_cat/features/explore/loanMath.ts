// Mirrors backend_cat/app/domain.py's calculate_max_loan_amount exactly —
// duplicated here (not called over the network) so the tenure slider can
// recompute the loan amount instantly while dragging, with no round-trip
// lag. interestRatePct is each bank's own real rate (product.interest_rate_pct
// from the API, already resolved with the fallback applied server-side — see
// get_bank_interest_rate_pct in domain.py) — no hardcoded rate here anymore.
export function calculateLoanAmountForTenure(
  maxEmi: number,
  tenureYears: number,
  interestRatePct: number,
): number {
  if (maxEmi <= 0 || tenureYears <= 0) return 0;
  const monthlyRate = interestRatePct / 100 / 12;
  const tenureMonths = tenureYears * 12;
  return (maxEmi * (1 - Math.pow(1 + monthlyRate, -tenureMonths))) / monthlyRate;
}

// The inverse of calculateLoanAmountForTenure: given a loan amount someone
// actually wants (not the bank's max), what EMI would repay it over this
// tenure at this bank's real interest rate. Standard EMI formula.
export function calculateEmiForLoanAmount(
  loanAmount: number,
  tenureYears: number,
  interestRatePct: number,
): number {
  if (loanAmount <= 0 || tenureYears <= 0) return 0;
  const monthlyRate = interestRatePct / 100 / 12;
  const tenureMonths = tenureYears * 12;
  const growth = Math.pow(1 + monthlyRate, tenureMonths);
  return (loanAmount * monthlyRate * growth) / (growth - 1);
}
