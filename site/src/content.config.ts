// Content collections read directly from ../content/ (one copy of each file) via the
// glob loader's `base` option. Schemas mirror pipeline/clearballot/validate.py.
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const status = z.enum(['draft', 'reviewed']);
const source = z.object({
  id: z.string(),
  title: z.string(),
  url: z.string().url(),
  publisher: z.string(),
  accessed: z.string(),
  kind: z.enum(['official', 'finance', 'legislative', 'news', 'candidate-site', 'endorsement']),
});

const common = {
  id: z.string(),
  title: z.string(),
  status,
  reviewed_by: z.string().nullable(),
  reviewed_at: z.string().nullable(),
  updated_at: z.string(),
  sources: z.array(source),
};

const measures = defineCollection({
  loader: glob({ pattern: '*.md', base: '../content/measures', generateId: ({ entry }) => entry.replace(/\.md$/, '') }),
  schema: z.object({
    ...common,
    ballot_number: z.string(),
    measure_type: z.string(),
    ballot_title: z.string(),
    yes_means: z.string(),
    no_means: z.string(),
  }),
});

const contests = defineCollection({
  loader: glob({ pattern: '*.md', base: '../content/contests', generateId: ({ entry }) => entry.replace(/\.md$/, '') }),
  schema: z.object({
    ...common,
    office: z.string(),
    district_type: z.enum(['statewide', 'cd', 'ld']),
    district_id: z.string(),
    district_number: z.number().int().nullable(),
    partisan: z.boolean(),
    term_note: z.string().nullable(),
    candidates: z.array(z.string()),
    ballot_page: z.number().int().optional(),
  }),
});

const finance = z.object({
  source: z.enum(['pdc', 'fec']),
  filer_id: z.string().nullable().optional(),
  url: z.string().url().nullable().optional(),
  total_raised: z.number().nullable(),
  total_spent: z.number().nullable(),
  cash_on_hand: z.number().nullable(),
  as_of: z.string(),
  top_contributors: z.array(
    z.object({
      name: z.string(),
      amount: z.number(),
      employer: z.string().nullable().optional(),
      occupation: z.string().nullable().optional(),
    }),
  ),
  small_donor_share: z.number().nullable().optional(),
});

const record = z.object({
  as_of: z.string(),
  sponsored_bills_url: z.string().url().optional(),
  sponsored_bills: z.array(
    z.object({ bill_id: z.string(), title: z.string().nullable(), status: z.string().nullable(), url: z.string().url() }),
  ),
  shortlist_votes: z.array(
    z.object({
      bill_id: z.string(),
      title: z.string().nullable(),
      vote: z.enum(['yea', 'nay', 'absent', 'excused', 'present', 'not recorded']).nullable(),
      chamber: z.string().nullable(),
      date: z.string().nullable(),
      url: z.string().url(),
      roll_call_url: z.string().url().nullable().optional(),
      question: z.string().nullable().optional(),
    }),
  ),
  pamphlet_cited_bills: z.array(z.string()).optional(),
});

const candidates = defineCollection({
  loader: glob({ pattern: '*.md', base: '../content/candidates', generateId: ({ entry }) => entry.replace(/\.md$/, '') }),
  schema: z.object({
    ...common,
    name: z.string(),
    contest: z.string(),
    party_preference: z.string().nullable(),
    incumbent: z.boolean(),
    current_office: z.string().nullable(),
    website: z.string().nullable(),
    pamphlet_statement_url: z.string().url().nullable(),
    pamphlet_statement_submitted: z.boolean().nullable().optional(),
    finance: finance.nullable(),
    finance_checked: z.string().nullable(),
    record: record.nullable(),
    endorsements: z.array(z.object({ org: z.string(), url: z.string().url(), self_reported: z.boolean() })),
  }),
});

const pages = defineCollection({
  loader: glob({ pattern: '*.md', base: '../content/pages', generateId: ({ entry }) => entry.replace(/\.md$/, '') }),
  schema: z.object({ ...common }),
});

export const collections = { measures, contests, candidates, pages };
