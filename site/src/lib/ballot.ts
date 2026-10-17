import { getCollection, type CollectionEntry } from 'astro:content';
import districtsJson from '../../../data/districts.json';
import contestsJson from '../../../data/contests.json';

export type Contest = CollectionEntry<'contests'>;
export type Candidate = CollectionEntry<'candidates'>;
export type Measure = CollectionEntry<'measures'>;

export const districts = districtsJson as {
  state_fips: string;
  county_geoid: string;
  geocoder_keys: { cd: string; ld: string; county: string };
  districts: Record<string, { district_type: string; district_number: number | null; name: string; measures: string[]; contests: string[] }>;
};

export async function loadAll() {
  const [measures, contests, candidates] = await Promise.all([
    getCollection('measures'),
    getCollection('contests'),
    getCollection('candidates'),
  ]);
  // Ballot order for measures comes from the parsed sample ballot.
  const order = new Map((contestsJson as { measures: { id: string }[] }).measures.map((m, i) => [m.id, i]));
  measures.sort((a, b) => (order.get(a.id) ?? 99) - (order.get(b.id) ?? 99));
  const contestById = new Map(contests.map((c) => [c.id, c]));
  const candidateById = new Map(candidates.map((c) => [c.id, c]));
  return { measures, contests, candidates, contestById, candidateById };
}

export function contestSort(a: Contest, b: Contest) {
  const order = { cd: 0, ld: 1, statewide: 2 } as const;
  const ta = order[a.data.district_type], tb = order[b.data.district_type];
  if (ta !== tb) return ta - tb;
  const na = a.data.district_number ?? 0, nb = b.data.district_number ?? 0;
  if (na !== nb) return na - nb;
  return a.data.office.localeCompare(b.data.office, undefined, { numeric: true });
}

export function money(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

export function pct(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return `${Math.round(n * 100)}%`;
}

/** Compact data embedded in the ballot page for client-side rendering. */
export function clientBallotData(measures: Measure[], contests: Contest[], candidates: Candidate[]) {
  const candById = new Map(candidates.map((c) => [c.id, c]));
  return {
    county_geoid: districts.county_geoid,
    districts: Object.fromEntries(
      Object.entries(districts.districts).map(([k, v]) => [k, { name: v.name, type: v.district_type, contests: v.contests }]),
    ),
    measures: measures.map((m) => ({ id: m.id, title: m.data.title, number: m.data.ballot_number, status: m.data.status })),
    contests: Object.fromEntries(
      contests.map((c) => [
        c.id,
        {
          title: c.data.title,
          type: c.data.district_type,
          term_note: c.data.term_note,
          candidates: c.data.candidates.map((slug) => {
            const k = candById.get(slug);
            return { slug, name: k?.data.name ?? slug, party: k?.data.party_preference ?? null, incumbent: k?.data.incumbent ?? false };
          }),
        },
      ]),
    ),
  };
}
