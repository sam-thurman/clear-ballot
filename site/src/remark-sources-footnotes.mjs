// Turns frontmatter `sources` into footnotes.
//
// GFM only parses `[^id]` as a footnote reference when a matching `[^id]: ...` definition
// exists in the same document. Our content files keep the definitions in frontmatter
// (`sources`), so this plugin (1) converts `[^id]` text into footnoteReference nodes and
// (2) appends a footnoteDefinition node per referenced source. remark-rehype then renders
// numbered superscript links and a footnotes section.
const CITE = /\[\^([A-Za-z0-9_.:-]+)\]/g;

export default function remarkSourcesFootnotes() {
  return (tree, file) => {
    const fm = file.data?.astro?.frontmatter ?? {};
    const sources = Array.isArray(fm.sources) ? fm.sources : [];
    const known = new Set(sources.map((s) => s.id));
    const referenced = [];
    const seen = new Set();

    const visit = (node, parent, index) => {
      if (node.type === 'html' && /^<!--\s*TODO/i.test(node.value || '')) {
        node.value = '<p class="small muted todo">Not yet written. This section will be added in a later update.</p>';
        return;
      }
      if (node.type === 'text' && parent && CITE.test(node.value)) {
        CITE.lastIndex = 0;
        const parts = [];
        let last = 0;
        for (const m of node.value.matchAll(CITE)) {
          if (!known.has(m[1])) continue;
          if (m.index > last) parts.push({ type: 'text', value: node.value.slice(last, m.index) });
          parts.push({ type: 'footnoteReference', identifier: m[1], label: m[1] });
          if (!seen.has(m[1])) { seen.add(m[1]); referenced.push(m[1]); }
          last = m.index + m[0].length;
        }
        if (last < node.value.length) parts.push({ type: 'text', value: node.value.slice(last) });
        if (parts.length) {
          parent.children.splice(index, 1, ...parts);
          return parts.length - 1; // extra nodes inserted
        }
        return;
      }
      if (node.children) {
        for (let i = 0; i < node.children.length; i++) {
          const extra = visit(node.children[i], node, i);
          if (typeof extra === 'number') i += extra;
        }
      }
    };
    visit(tree, null, 0);

    for (const id of referenced) {
      const s = sources.find((x) => x.id === id);
      const suffix = s.kind === 'news' ? ' (news report)' : s.kind === 'candidate-site' ? " (candidate's own site)" : '';
      tree.children.push({
        type: 'footnoteDefinition',
        identifier: s.id,
        label: s.id,
        children: [
          {
            type: 'paragraph',
            children: [
              { type: 'link', url: s.url, children: [{ type: 'text', value: s.title }] },
              { type: 'text', value: ` — ${s.publisher}, accessed ${s.accessed}${suffix}` },
            ],
          },
        ],
      });
    }
  };
}
