// Cloudflare Pages Function: CORS proxy for the U.S. Census geocoder.
// GET /api/geocode?address=<one-line address>
// Returns { matched, matched_address, lat, lon, county, cd, ld } with CORS headers.
// Responses are cached at the edge for 24 hours per normalized address. Nothing is logged or stored.

const GEOCODER = 'https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress';
const KEYS = {
  cd: '120th Congressional Districts',
  ld: '2026 State Legislative Districts - Lower',
  county: 'Counties',
};
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function json(body: unknown, status = 200, extra: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...CORS, ...extra },
  });
}

export const onRequestOptions: PagesFunction = async () => new Response(null, { status: 204, headers: CORS });

export const onRequestGet: PagesFunction = async ({ request }) => {
  const url = new URL(request.url);
  const address = (url.searchParams.get('address') || '').trim().replace(/\s+/g, ' ');
  if (!address || address.length > 200) {
    return json({ error: 'address query parameter is required (max 200 characters)' }, 400);
  }

  const upstream = new URL(GEOCODER);
  upstream.searchParams.set('address', address);
  upstream.searchParams.set('benchmark', 'Public_AR_Current');
  upstream.searchParams.set('vintage', 'Current_Current');
  upstream.searchParams.set('format', 'json');

  const cache = caches.default;
  const cacheKey = new Request(`https://cache.clear-ballot.invalid/geocode?a=${encodeURIComponent(address.toLowerCase())}`);
  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  let data: any;
  try {
    const res = await fetch(upstream.toString(), { headers: { 'User-Agent': 'clear-ballot/0.1 (+https://github.com/sam-thurman/clear-ballot)' } });
    if (!res.ok) return json({ error: `geocoder returned ${res.status}` }, 502);
    data = await res.json();
  } catch (e) {
    return json({ error: 'geocoder unreachable' }, 502);
  }

  const match = data?.result?.addressMatches?.[0];
  let body;
  if (!match) {
    body = { matched: false };
  } else {
    const g = match.geographies || {};
    const first = (k: string) => (g[k] && g[k][0] && g[k][0].GEOID) || null;
    body = {
      matched: true,
      matched_address: match.matchedAddress,
      lat: match.coordinates?.y ?? null,
      lon: match.coordinates?.x ?? null,
      county: first(KEYS.county),
      cd: first(KEYS.cd),
      ld: first(KEYS.ld),
    };
  }
  const response = json(body, 200, { 'Cache-Control': 'public, max-age=86400' });
  await cache.put(cacheKey, response.clone());
  return response;
};
