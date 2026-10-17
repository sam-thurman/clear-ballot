// Post-build gate: every content file with `status: draft` must produce a page containing the
// draft banner, and every content page must contain the Report-an-error link. Fails the build otherwise.
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const dist = join(root, 'dist');
const content = join(root, '..', 'content');
const BANNER = 'Unreviewed draft.';
const REPORT = 'data-report-error';

let checked = 0, drafts = 0;
const errors = [];
for (const [dir, route] of [['measures', 'measures'], ['contests', 'contests'], ['candidates', 'candidates'], ['pages', '']]) {
  for (const f of readdirSync(join(content, dir)).filter((f) => f.endsWith('.md'))) {
    const md = readFileSync(join(content, dir, f), 'utf8');
    const status = (md.match(/^status:\s*(\w+)/m) || [])[1];
    const id = f.replace(/\.md$/, '');
    const html = join(dist, route ? `${route}/${id}.html` : `${id}.html`);
    if (!existsSync(html)) { errors.push(`${dir}/${f}: no built page at ${html}`); continue; }
    const out = readFileSync(html, 'utf8');
    checked++;
    if (!out.includes(REPORT)) errors.push(`${dir}/${f}: built page has no Report-an-error link`);
    if (status === 'draft') {
      drafts++;
      if (!out.includes(BANNER)) errors.push(`${dir}/${f}: status is draft but the built page has no draft banner`);
    } else if (status === 'reviewed') {
      if (out.includes(BANNER)) errors.push(`${dir}/${f}: status is reviewed but the built page shows the draft banner`);
    } else {
      errors.push(`${dir}/${f}: unknown status ${status}`);
    }
  }
}
for (const e of errors) console.error('ERROR', e);
console.log(`check-banner: ${checked} content pages checked, ${drafts} drafts show the banner, ${errors.length} errors`);
process.exit(errors.length ? 1 : 0);
