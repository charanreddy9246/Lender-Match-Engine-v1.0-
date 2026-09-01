// How Property Type's 14 values are grouped under sub-headings in the
// sidebar — mirrors the client workbook's own Classification grouping
// (Residential / Commercial / Industrial / Residential cum Commercial).
export const PROPERTY_TYPE_GROUPS: { heading: string; values: string[] }[] = [
  {
    heading: "Residential",
    values: [
      "residential_vacant_land",
      "residential_apartment",
      "residential_independent_building",
      "residential_semi_independent_uds",
    ],
  },
  {
    heading: "Commercial",
    values: [
      "commercial_farm_land",
      "commercial_vacant_land",
      "commercial_independent_building",
      "commercial_semi_independent_uds",
      "commercial_temporary_structure",
    ],
  },
  {
    heading: "Industrial",
    values: ["industrial_vacant_land", "industrial_warehouse"],
  },
  {
    heading: "Residential cum Commercial",
    values: ["res_cum_comm_independent_building", "res_cum_comm_building", "res_cum_comm_multi_unit"],
  },
];
