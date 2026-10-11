import { enterTree } from './flow.mjs'; import { shot } from './capture_lib.mjs';
const { browser, page } = await enterTree();
console.log('shot', await shot(page, 'tree_overview_v1'));
await browser.close();
