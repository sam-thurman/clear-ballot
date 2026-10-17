// @ts-check
import { defineConfig } from 'astro/config';
import { unified } from '@astrojs/markdown-remark';
import remarkSourcesFootnotes from './src/remark-sources-footnotes.mjs';

// https://astro.build/config
export default defineConfig({
  site: 'https://clear-ballot.pages.dev',
  output: 'static',
  trailingSlash: 'never',
  build: { format: 'file' },
  markdown: {
    // Use the unified (remark/rehype) processor explicitly: our citation footnotes are produced
    // by a remark plugin, and Astro 7's default Markdown processor does not run remark plugins.
    processor: unified({ remarkPlugins: [remarkSourcesFootnotes] }),
  },
});
