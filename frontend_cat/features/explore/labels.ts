// Mirrors backend_cat/app/explore.py's VALUE_LABELS — used to display the
// raw values inside each result card (facets already carry labels from the
// API, but the per-bank result rows only carry raw values).
const VALUE_LABELS: Record<string, string> = {
  salaried: "Salaried",
  self_employed: "Self-Employed",
  pensioner: "Pensioner",
  cash_income: "Cash Income",
  nri: "NRI",
  residential_vacant_land: "Residential — Vacant Land",
  residential_apartment: "Residential — Apartment",
  residential_independent_building: "Residential — Independent Building",
  residential_semi_independent_uds: "Residential — Semi-Independent (UDS)",
  commercial_farm_land: "Commercial — Farm Land",
  commercial_vacant_land: "Commercial — Vacant Land",
  commercial_independent_building: "Commercial — Independent Building",
  commercial_semi_independent_uds: "Commercial — Semi-Independent (UDS)",
  commercial_temporary_structure: "Commercial — Temporary Structure",
  industrial_vacant_land: "Industrial — Vacant Land",
  industrial_warehouse: "Industrial — Warehouse",
  res_cum_comm_independent_building: "Residential cum Commercial — Independent Building",
  res_cum_comm_building: "Residential cum Commercial — Building",
  res_cum_comm_multi_unit: "Residential cum Commercial — Multi-Unit",
  self_occupied: "Self-Occupied",
  let_out: "Let-Out",
  lease: "Lease",
  new_purchase: "New Purchase",
  resale: "Resale",
  under_construction: "Under Construction",
  take_over: "Take Over",
  standard_urban: "Standard Urban",
  peri_urban: "Peri-Urban",
  rural: "Rural",
};

export function labelFor(value: string): string {
  return VALUE_LABELS[value] ?? value;
}
