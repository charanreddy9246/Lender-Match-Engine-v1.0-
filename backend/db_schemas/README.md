# Database schemas

Two databases, two folders — kept separate so it's always obvious which
schema file belongs to which server.

- **`supabase/`** — the original Birbal Club database. Holds our own
  fictional-but-realistic 100-bank dataset. This is what `DATABASE_URL` in
  `.env` points at by default today (the Postgres-server line is commented
  out, ready to swap in when needed — see the root `.env` file).

- **`postgres_server/`** — the new `Lender_Matching` database on our own
  Postgres server (32.198.162.66). This is where the client's data will
  eventually live — same exact column names the client uses, but not real
  values yet. It's currently empty.

Both folders use the **same table design** (banks → home_loan_products →
eligibility_rules, with a shared `attributes` catalog) on purpose — the
client's real attribute names just become new rows in `attributes`, not new
columns or a different schema shape. That keeps the backend's code working
unchanged no matter which database `DATABASE_URL` points at.

The actual source of truth for this design is
`backend/app/database.py` (SQLAlchemy models) — these `.sql` files are a
plain-SQL mirror of that, kept here for reference and for running directly
against a server with `psql` if needed. If you change `database.py`, update
both `.sql` files to match.

## Open question — not yet decided

The manager raised folding the `attributes` table into `eligibility_rules`
directly (so a rule row carries its own label/category/data_type instead of
pointing at a shared catalog row). Not implemented — still being discussed.
See `postgres_server/NOTES.md`.
