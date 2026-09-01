# Open design question — not decided yet

Manager suggested folding the `attributes` table directly into
`eligibility_rules` — i.e. each rule row would carry its own `label`,
`category`, and `data_type` instead of pointing at a shared row in a
separate `attributes` catalog table.

**Not implemented.** Still being checked/decided. `schema.sql` in this
folder keeps the same two-table design (`attributes` + `eligibility_rules`)
as Supabase for now. If this changes, update `schema.sql` here — the
Supabase schema stays as-is either way, since the two databases don't have
to share a design forever, just for now.
