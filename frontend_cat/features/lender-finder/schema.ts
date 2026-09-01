import { z } from "zod";

import { DOCUMENT_TYPES, EMPLOYMENT_TYPES, INCOME_FIELD_BY_EMPLOYMENT_TYPE, PROPERTY_TYPES } from "@/lib/api/types";

const employmentValues = EMPLOYMENT_TYPES.map((o) => o.value) as [string, ...string[]];
const documentValues = DOCUMENT_TYPES.map((o) => o.value) as [string, ...string[]];
const propertyValues = PROPERTY_TYPES.map((o) => o.value) as [string, ...string[]];

export const lenderFinderSchema = z
  .object({
    cibil_score: z
      .number({ error: "Enter your CIBIL score" })
      .int()
      .min(300, "CIBIL score must be at least 300")
      .max(900, "CIBIL score can't exceed 900"),
    loan_amount_required: z
      .number({ error: "Enter the loan amount you need" })
      .int()
      .positive("Loan amount must be greater than 0"),
    employment_type: z.enum(employmentValues, { error: "Select your employment type" }),
    // Only the field matching the selected employment_type is actually
    // required — enforced below in superRefine, since which one applies is
    // decided dynamically, not statically.
    net_monthly_salary: z.number().int().positive().optional(),
    annual_turnover: z.number().int().positive().optional(),
    annual_gross_receipts: z.number().int().positive().optional(),
    monthly_pension: z.number().int().positive().optional(),
    has_co_borrower: z.boolean(),
    documents_available: z
      .array(z.enum(documentValues))
      .refine((docs) => docs.includes("bank_statement"), {
        message: "Bank statement is required",
      }),
    property_type: z.enum(propertyValues, { error: "Select the property type" }),
  })
  .superRefine((values, ctx) => {
    const requirement = INCOME_FIELD_BY_EMPLOYMENT_TYPE[values.employment_type as keyof typeof INCOME_FIELD_BY_EMPLOYMENT_TYPE];
    if (requirement && !values[requirement.field]) {
      ctx.addIssue({ code: "custom", message: `Enter your ${requirement.label.split(" (")[0].toLowerCase()}`, path: [requirement.field] });
    }
  });

export type LenderFinderFormValues = z.infer<typeof lenderFinderSchema>;
