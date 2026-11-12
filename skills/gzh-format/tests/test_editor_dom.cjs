/* 真实 DOM 回归；先安装 Playwright，并通过 NODE_PATH 或本地依赖提供运行时。 */
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const editorPath = path.join(__dirname, '../assets/editor.js');
const baseline = {
  schema: 'gzh-edit/v1', article_id: 'independent-fixture', revision: 0,
  title: '已有文章标题',
  source_sha256: 'source-hash', html_sha256: 'html-hash',
  images: ['https://example.invalid/1.png', 'https://example.invalid/2.png'],
  headings: ['1. 编号标题', '保留微标题', '2. 一级标题'],
  blocks: [
    { id: 'b1', kind: 'paragraph', runs: [
      { text: '开头', red: false, bold: false, href: '', marks: [] },
      { text: '链接文字', red: true, bold: true, href: 'https://example.invalid/read', marks: ['underline'] },
      { text: '结尾删除', red: false, bold: false, href: '', marks: [] },
    ] },
    { id: 'b3', kind: 'paragraph', runs: [{ text: '下一段正文', red: false, bold: false, href: '', marks: [] }] },
    { id: 'b2', kind: 'subheading', runs: [{ text: '1. 编号标题', red: false, bold: true, href: '', marks: [] }] },
    { id: 'b4', kind: 'micro', runs: [{ text: '保留微标题', red: false, bold: true, href: '', marks: [] }] },
    { id: 'b5', kind: 'h2', runs: [{ text: '2. 一级标题', red: false, bold: true, href: '', marks: [] }] },
  ],
};
let browser;
before(async () => {
  assert.ok(fs.existsSync(editorPath), '共享预览编辑器尚未实现');
  const options = { headless: true };
  if (process.env.GZH_TEST_BROWSER) options.executablePath = process.env.GZH_TEST_BROWSER;
  browser = await chromium.launch(options);
});
after(async () => { if (browser) await browser.close(); });

async function fixture(t, prefilled = false, withBridge = false, emptyBlock = false) {
  const page = await browser.newPage();
  page.setDefaultTimeout(5000);
  t.after(() => page.close());
  await page.route(/^https?:/, route => route.abort());
  const data = structuredClone(baseline);
  if (emptyBlock) data.blocks[1].runs = [];
  if (withBridge) data.save_bridge = { save_url: '/api/save', state_url: '/api/state', session_token: 'fixture-session' };
  const json = JSON.stringify(data).replace(/</g, '\\u003c');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'gzh-editor-dom-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const file = path.join(directory, 'fixture.html');
  const original = prefilled ? `<span data-original-look="kept" style="letter-spacing:2px;font-size:19px">开头<a href="${baseline.blocks[0].runs[1].href}" style="color:#DC2626;text-decoration:underline"><strong style="font-weight:800"><span leaf="">链接文字</span></strong></a>结尾删除</span>` : '';
  fs.writeFileSync(file, `<meta charset="utf-8"><div id="gzh-editor-toolbar"></div><label for="gzh-title">文章标题</label><input id="gzh-title" value="${baseline.title}"><div id="gzh-content"><p data-gzh-edit-id="b1">${original}</p><img src="${baseline.images[0]}"><p data-gzh-edit-id="b3"></p><h3 data-gzh-edit-id="b2"></h3><img src="${baseline.images[1]}"><h4 data-gzh-edit-id="b4" style="font-size:16px"></h4><p data-gzh-edit-id="b5" data-gzh-edit-part="number">02</p><p data-gzh-edit-id="b5"></p></div><script id="gzh-edit-data" type="application/json">${json}</script>`);
  if (withBridge) {
    await page.route('http://127.0.0.1:47321/fixture.html', route => route.fulfill({ contentType: 'text/html', body: fs.readFileSync(file, 'utf8') }));
    await page.goto('http://127.0.0.1:47321/fixture.html');
  } else await page.goto(pathToFileURL(file).href);
  await page.addScriptTag({ path: editorPath });
  await page.addStyleTag({ path: path.join(__dirname, '../assets/editor.css') });
  return page;
}
async function select(page, id, start, end, endId = id) {
  await page.evaluate(({ id, start, end, endId }) => {
    const el = document.querySelector(`[data-gzh-edit-id="${id}"]`);
    const endEl = document.querySelector(`[data-gzh-edit-id="${endId}"]`);
    function point(target, offset) {
      const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT);
      const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
      for (const node of nodes) {
        if (offset <= node.length) return [node, offset];
        offset -= node.length;
      }
      return [target, target.childNodes.length];
    }
    const range = document.createRange(); range.setStart(...point(el, start)); range.setEnd(...point(endEl, end));
    el.focus(); const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
  }, { id, start, end, endId });
}
const exported = page => page.evaluate(() => window.gzhEditor.exportPackage());

test('独立标题参与未保存提示、保存后撤销与再次保存', async t => {
  const page = await fixture(t, true, true);
  const bodyBefore = await page.locator('#gzh-content').innerHTML();
  const submissions = [];
  await page.route('**/api/save', route => {
    const body = route.request().postDataJSON(); submissions.push(body);
    return route.fulfill({ json: savedResponse(body) });
  });
  assert.equal(await page.getByLabel('文章标题').inputValue(), baseline.title);
  await page.getByLabel('文章标题').fill('写后加工的标题');
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  assert.equal((await exported(page)).title, '写后加工的标题');
  await page.evaluate(() => gzhEditor.saveDraft());
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
  await page.evaluate(() => gzhEditor.undo());
  assert.equal(await page.getByLabel('文章标题').inputValue(), baseline.title);
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  await page.evaluate(() => gzhEditor.saveDraft());
  assert.equal(submissions[1].package.title, baseline.title);
  assert.equal(submissions[1].package.revision, 1);
  assert.equal(await page.locator('#gzh-content').innerHTML(), bodyBefore);
  await page.evaluate(() => gzhEditor.redo());
  assert.equal(await page.getByLabel('文章标题').inputValue(), '写后加工的标题');
  await page.evaluate(() => gzhEditor.setEditing(false));
  assert.equal(await page.getByLabel('文章标题').getAttribute('readonly'), '');
});

test('保存请求期间继续改标题只保存提交时版本，后来输入仍未保存', async t => {
  const page = await fixture(t, false, true);
  let pending;
  await page.route('**/api/save', route => { pending = route; });
  await page.getByLabel('文章标题').fill('首次提交标题');
  const saving = page.evaluate(() => gzhEditor.saveDraft());
  await page.waitForFunction(() => document.getElementById('gzhSaveDraftBtn').disabled);
  await page.getByLabel('文章标题').fill('保存期间继续修改标题');
  while (!pending) await new Promise(resolve => setImmediate(resolve));
  const body = pending.request().postDataJSON();
  await pending.fulfill({ json: savedResponse(body) });
  assert.equal(await saving, true);
  assert.equal(body.package.title, '首次提交标题');
  assert.equal(await page.getByLabel('文章标题').inputValue(), '保存期间继续修改标题');
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  assert.match(await page.locator('#gzh-editor-status').innerText(), /未保存/);
});

test('标题保存响应缺失或错题不能冒称已保存', async t => {
  const page = await fixture(t, false, true);
  await page.route('**/api/save', route => {
    const result = savedResponse(route.request().postDataJSON()); delete result.package.title;
    return route.fulfill({ json: result });
  });
  await page.getByLabel('文章标题').fill('要求持久保存的标题');
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), false);
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  assert.match(await page.locator('#gzh-editor-status').innerText(), /基线不完整/);
});

test('标题中的C1控制字符不能导出或提交', async t => {
  const page = await fixture(t, false, true);
  let submissions = 0;
  await page.route('**/api/save', route => { submissions += 1; return route.abort(); });
  for (const control of ['\u0085', '\u009f']) {
    await page.getByLabel('文章标题').fill('标题' + control + '控制字符');
    const error = await page.evaluate(() => { try { gzhEditor.exportPackage(); return ''; } catch (error) { return error.message; } });
    assert.match(error, /控制字符/);
    assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), false);
  }
  assert.equal(submissions, 0);
});

test('默认只开放注册文字块，保留编号和图片顺序', async t => {
  const page = await fixture(t);
  assert.equal(await page.locator('[data-gzh-edit-id="b1"]').getAttribute('contenteditable'), 'true');
  assert.equal(await page.locator('img').first().getAttribute('contenteditable'), null);
  assert.equal(await page.locator('h3').innerText(), baseline.headings[0]);
  assert.deepEqual(await page.locator('img').evaluateAll(nodes => nodes.map(x => x.src)), baseline.images);
  await page.evaluate(() => gzhEditor.setEditing(false));
  assert.equal(await page.locator('p').first().getAttribute('contenteditable'), 'false');
});

test('跨 span 取消红色保留粗体、链接和装饰，粗体可单独切换', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 1, 7);
  await page.evaluate(() => gzhEditor.applyFormat('red', false));
  let pack = await exported(page);
  const link = pack.blocks[0].runs.find(x => x.href);
  assert.equal(link.red, false); assert.equal(link.bold, true);
  assert.deepEqual(link.marks, ['underline']);
  await select(page, 'b1', 2, 6);
  await page.evaluate(() => gzhEditor.applyFormat('red', true));
  await page.evaluate(() => gzhEditor.applyFormat('bold', false));
  pack = await exported(page);
  const changed = pack.blocks[0].runs.find(x => x.href);
  assert.equal(changed.red, true); assert.equal(changed.bold, false);
  assert.equal(changed.href, baseline.blocks[0].runs[1].href);
});

test('真实删除和输入进入修改包，撤销重做恢复文字与样式', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 8, 10);
  await page.keyboard.press('Backspace');
  await page.keyboard.insertText('新稿');
  let pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾新稿');
  await page.evaluate(() => gzhEditor.undo());
  assert.equal((await exported(page)).blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾');
  await page.evaluate(() => gzhEditor.redo());
  pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾新稿');
  assert.equal(pack.blocks[0].runs.find(x => x.href).bold, true);
});

test('删除整行按钮清空当前正文或标题块，并可撤销恢复', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 0, 2);
  await page.getByRole('button', { name: '删除整行', exact: true }).click();
  let pack = await exported(page);
  assert.deepEqual(pack.blocks.find(block => block.id === 'b1').runs, []);
  assert.equal(await page.locator('[data-gzh-edit-id="b1"]').getAttribute('data-gzh-edit-empty'), '1');
  await page.locator('[data-gzh-edit-id="b5"][data-gzh-edit-part="number"]').click();
  await page.getByRole('button', { name: '删除整行', exact: true }).click();
  pack = await exported(page);
  assert.deepEqual(pack.blocks.find(block => block.id === 'b5').runs, []);
  assert.equal(await page.locator('[data-gzh-edit-id="b5"][data-gzh-edit-part="number"]').getAttribute('data-gzh-edit-empty'), '1');
  await page.evaluate(() => gzhEditor.undo());
  assert.equal((await exported(page)).blocks.find(block => block.id === 'b5').runs[0].text, '2. 一级标题');
  await page.evaluate(() => gzhEditor.undo());
  assert.equal((await exported(page)).blocks.find(block => block.id === 'b1').runs[0].text, '开头');
});

test('添加一行插入当前光标位置，保留样式并支持章节编号激活当前块', async t => {
  const page = await fixture(t);
  // 字符偏移 1 位于“开”和“头”之间；中文字符各占一个 UTF-16 单元。
  await select(page, 'b1', 1, 1);
  await page.getByRole('button', { name: '添加一行', exact: true }).click();
  const pack = await exported(page);
  const runs = pack.blocks.find(block => block.id === 'b1').runs;
  assert.equal(runs.map(run => run.text).join(''), '开\n头链接文字结尾删除');
  assert.equal(runs[0].red, false);
  assert.equal(runs[0].bold, false);
  await page.evaluate(() => gzhEditor.undo());
  assert.equal((await exported(page)).blocks.find(block => block.id === 'b1').runs.map(run => run.text).join(''), '开头链接文字结尾删除');
  await page.locator('[data-gzh-edit-id="b5"][data-gzh-edit-part="number"]').click();
  await page.getByRole('button', { name: '添加一行', exact: true }).click();
  assert.equal((await exported(page)).blocks.find(block => block.id === 'b5').runs.map(run => run.text).join(''), '2. 一级标题\n');
});

test('一级章节序号可单独修改/删除，二级标题序号可选中修改/删除', async t => {
  const page = await fixture(t);
  const number = page.locator('[data-gzh-edit-id="b5"][data-gzh-edit-part="number"]');
  await number.selectText();
  await page.keyboard.insertText('07');
  let pack = await exported(page);
  assert.equal(pack.blocks.find(block => block.id === 'b5').number, '07');

  await select(page, 'b2', 0, 3);
  await page.keyboard.press('Backspace');
  pack = await exported(page);
  assert.equal(pack.blocks.find(block => block.id === 'b2').runs.map(run => run.text).join(''), '编号标题');

  await number.selectText();
  await page.keyboard.press('Backspace');
  pack = await exported(page);
  assert.equal(pack.blocks.find(block => block.id === 'b5').number, '');
  assert.equal(await number.isVisible(), true);
});

test('粘贴只取纯文字，保留基线链接且不接收 HTML', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 6, 10);
  await page.locator('p').first().evaluate(el => {
    const data = new DataTransfer(); data.setData('text/plain', '<新文字>'); data.setData('text/html', '<img src=x onerror="window.pwned=true">');
    el.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: data }));
  });
  const pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字<新文字>');
  assert.equal(await page.locator('p img').count(), 0);
  assert.equal(pack.blocks[0].runs.find(x => x.href).href, baseline.blocks[0].runs[1].href);
});

test('未知 DOM 结构不能静默写进修改包', async t => {
  const page = await fixture(t);
  await page.locator('p').first().evaluate(el => { el.appendChild(document.createElement('iframe')); });
  const error = await page.evaluate(() => { try { gzhEditor.exportPackage(); return ''; } catch (error) { return error.message; } });
  assert.match(error, /结构|不支持|格式/);
});

test('离线页只显示禁用的保存草稿，内部模型保留基线元数据', async t => {
  const page = await fixture(t);
  const pack = await exported(page);
  for (const key of ['schema', 'article_id', 'revision', 'source_sha256', 'html_sha256', 'images', 'headings']) assert.deepEqual(pack[key], baseline[key]);
  assert.ok(pack.saved_at);
  assert.deepEqual(Object.keys(pack.blocks[0]).sort(), ['id', 'runs']);
  assert.equal(await page.getByRole('button', { name: '保存草稿', exact: true }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: /导出|另存/ }).count(), 0);
  assert.match(await page.locator('#gzh-editor-status').innerText(), /请从本地保存服务打开/);
});

function savedResponse(body, status = 'saved') {
  const pack = structuredClone(body.package);
  delete pack.saved_at;
  if (status === 'saved') pack.revision += 1;
  pack.source_sha256 = `source-${pack.revision}`; pack.html_sha256 = `html-${pack.revision}`;
  pack.blocks = pack.blocks.map((block, index) => ({ ...block, kind: baseline.blocks[index].kind }));
  return { status, package: pack };
}

test('保存草稿实际POST并采用响应基线，未触发文件下载', async t => {
  const page = await fixture(t, false, true);
  let submitted; let downloads = 0;
  page.on('download', () => { downloads += 1; });
  await page.route('**/api/save', route => { submitted = route.request().postDataJSON(); return route.fulfill({ json: savedResponse(submitted) }); });
  await select(page, 'b1', 10, 10); await page.keyboard.insertText('改');
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  await page.getByRole('button', { name: '保存草稿', exact: true }).click();
  await page.waitForFunction(() => document.getElementById('gzh-editor-status').textContent.includes('已保存'));
  assert.equal(submitted.session_token, 'fixture-session');
  assert.equal(submitted.package.revision, 0); assert.equal(submitted.package.save_bridge, undefined);
  assert.equal((await exported(page)).revision, 1);
  assert.equal((await exported(page)).source_sha256, 'source-1');
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
  assert.equal(downloads, 0);
});

test('自动保存每次只提交当前未保存版本，保存后空闲 tick 不重复提交', async t => {
  const page = await fixture(t, false, true);
  assert.equal(await page.evaluate(() => gzhEditor.autoSaveInterval), 120000);
  let submissions = 0;
  await page.route('**/api/save', route => {
    submissions += 1;
    const body = route.request().postDataJSON();
    return route.fulfill({ json: savedResponse(body) });
  });
  await select(page, 'b1', 10, 10);
  await page.keyboard.insertText('自动保存');
  assert.equal(await page.evaluate(() => gzhEditor.autoSaveTick()), true);
  await page.waitForFunction(() => !gzhEditor.isDirty());
  assert.equal(submissions, 1);
  assert.match(await page.locator('#gzh-editor-autosave').innerText(), /最近保存/);
  assert.equal(await page.evaluate(() => gzhEditor.autoSaveTick()), false);
  assert.equal(submissions, 1);
});

test('保存失败保持未保存状态，重试仍使用原基线', async t => {
  const page = await fixture(t, false, true);
  let submitted;
  await page.route('**/api/save', route => { submitted = route.request().postDataJSON(); return route.fulfill({ status: 409, json: { error: '源文件已变化' } }); });
  await select(page, 'b1', 10, 10); await page.keyboard.insertText('改');
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), false);
  assert.match(await page.locator('#gzh-editor-status').innerText(), /保存失败.*源文件已变化/);
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  assert.equal((await exported(page)).revision, 0);
  assert.equal(await page.getByRole('button', { name: '保存草稿', exact: true }).isEnabled(), true);
  await page.unroute('**/api/save');
  await page.route('**/api/save', route => { submitted = route.request().postDataJSON(); return route.fulfill({ json: savedResponse(submitted) }); });
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), true);
  assert.equal(submitted.package.revision, 0);
});

test('保存后仍可撤销重做，再次保存使用新修订基线', async t => {
  const page = await fixture(t, false, true);
  const submissions = [];
  await page.route('**/api/save', route => { const body = route.request().postDataJSON(); submissions.push(body); return route.fulfill({ json: savedResponse(body) }); });
  await select(page, 'b1', 10, 10); await page.keyboard.insertText('改');
  await page.evaluate(() => gzhEditor.saveDraft());
  await page.evaluate(() => gzhEditor.undo());
  assert.equal((await exported(page)).blocks[0].runs.map(run => run.text).join(''), '开头链接文字结尾删除');
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  await page.evaluate(() => gzhEditor.redo());
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
  await page.evaluate(() => gzhEditor.undo());
  await page.evaluate(() => gzhEditor.saveDraft());
  assert.equal(submissions[1].package.revision, 1);
  assert.equal(submissions[1].package.source_sha256, 'source-1');
  assert.equal((await exported(page)).revision, 2);
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
  await page.evaluate(() => gzhEditor.redo());
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
});

test('保存中可继续输入且不重复提交，响应只标记提交快照已保存', async t => {
  const page = await fixture(t, false, true);
  let resolveRequest; let received; let requests = 0;
  const blocked = new Promise(resolve => { resolveRequest = resolve; });
  await page.route('**/api/save', async route => { requests += 1; received = route.request().postDataJSON(); await blocked; await route.fulfill({ json: savedResponse(received) }); });
  await select(page, 'b1', 10, 10); await page.keyboard.insertText('A');
  await page.evaluate(() => { window.pendingSave = gzhEditor.saveDraft(); });
  await page.waitForFunction(() => document.querySelector('#gzhSaveDraftBtn').disabled);
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), false);
  await select(page, 'b1', 11, 11); await page.keyboard.insertText('B');
  resolveRequest();
  assert.equal(await page.evaluate(() => window.pendingSave), true);
  assert.equal(requests, 1);
  assert.equal(received.package.blocks[0].runs.map(run => run.text).join(''), '开头链接文字结尾删除A');
  assert.equal((await exported(page)).blocks[0].runs.map(run => run.text).join(''), '开头链接文字结尾删除AB');
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  assert.match(await page.locator('#gzh-editor-status').innerText(), /仍有|还有|未保存/);
});

for (const failure of ['network', 'http500', 'invalid-json', 'invalid-package']) {
  test(`保存A后的${failure}丢失确认，下一次先确认A再保存新增B`, async t => {
    const page = await fixture(t, false, true);
    let release; let diskWrites = 0; let confirmed; let firstBody;
    const requests = []; const blocked = new Promise(resolve => { release = resolve; });
    await page.route('**/api/save', async route => {
      const body = route.request().postDataJSON(); requests.push(body);
      if (requests.length === 1) {
        firstBody = body; confirmed = savedResponse(body); diskWrites += 1; await blocked;
        if (failure === 'network') return route.abort('failed');
        if (failure === 'http500') return route.fulfill({ status: 500, json: { error: '回复前连接失败' } });
        if (failure === 'invalid-json') return route.fulfill({ contentType: 'application/json', body: '{broken' });
        return route.fulfill({ json: { status: 'saved', package: { revision: 1 } } });
      }
      if (requests.length === 2) {
        if (JSON.stringify(body) !== JSON.stringify(firstBody)) return route.fulfill({ status: 409, json: { error: '旧修订不能覆盖' } });
        return route.fulfill({ json: { ...confirmed, status: 'already-imported' } });
      }
      if (body.package.revision !== 1) return route.fulfill({ status: 409, json: { error: '必须采用已确认修订' } });
      diskWrites += 1; return route.fulfill({ json: savedResponse(body) });
    });
    await select(page, 'b1', 10, 10); await page.keyboard.insertText('A');
    await page.evaluate(() => { window.firstSave = gzhEditor.saveDraft(); });
    await page.waitForFunction(() => document.getElementById('gzhSaveDraftBtn').disabled);
    await select(page, 'b1', 11, 11); await page.keyboard.insertText('B');
    release();
    assert.equal(await page.evaluate(() => window.firstSave), false);
    assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
    assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), true);
    assert.equal(requests.length, 3); assert.equal(diskWrites, 2);
    assert.deepEqual(requests[1], firstBody);
    assert.equal(requests[2].package.blocks[0].runs.map(run => run.text).join(''), '开头链接文字结尾删除AB');
    assert.equal((await exported(page)).revision, 2);
    assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
    await page.evaluate(() => gzhEditor.undo());
    assert.equal((await exported(page)).blocks[0].runs.map(run => run.text).join(''), '开头链接文字结尾删除A');
    assert.equal(await page.evaluate(() => gzhEditor.isDirty()), true);
  });
}

test('相同内容保存回复丢失后原样确认重试，不重复落盘', async t => {
  const page = await fixture(t, false, true);
  const requests = []; let stored;
  await page.route('**/api/save', route => {
    const body = route.request().postDataJSON(); requests.push(body);
    if (requests.length === 1) { stored = savedResponse(body); return route.abort('failed'); }
    return route.fulfill({ json: { ...stored, status: 'already-imported' } });
  });
  await select(page, 'b1', 10, 10); await page.keyboard.insertText('A');
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), false);
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), true);
  assert.deepEqual(requests[1], requests[0]);
  assert.equal(requests.length, 2);
  assert.equal((await exported(page)).revision, 1);
  assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
});

for (const refusal of [400, 403, 409]) {
  test(`明确${refusal}拒绝清除待确认提交，下次直接提交当前新稿`, async t => {
    const page = await fixture(t, false, true);
    const requests = [];
    await page.route('**/api/save', route => {
      const body = route.request().postDataJSON(); requests.push(body);
      if (requests.length === 1) return route.fulfill({ status: refusal, json: { error: '明确拒绝' } });
      return route.fulfill({ json: savedResponse(body) });
    });
    await select(page, 'b1', 10, 10); await page.keyboard.insertText('A');
    assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), false);
    await select(page, 'b1', 11, 11); await page.keyboard.insertText('B');
    assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), true);
    assert.equal(requests.length, 2);
    assert.equal(requests[1].package.revision, 0);
    assert.equal(requests[1].package.blocks[0].runs.map(run => run.text).join(''), '开头链接文字结尾删除AB');
    assert.equal(await page.evaluate(() => gzhEditor.isDirty()), false);
  });
}

test('already-imported响应可确认已保存，离页只在有未保存修改时提醒', async t => {
  const page = await fixture(t, false, true);
  await page.route('**/api/save', route => route.fulfill({ json: savedResponse(route.request().postDataJSON(), 'already-imported') }));
  const warned = () => page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented; });
  assert.equal(await warned(), false);
  await select(page, 'b1', 10, 10); await page.keyboard.insertText('改');
  assert.equal(await warned(), true);
  assert.equal(await page.evaluate(() => gzhEditor.saveDraft()), true);
  assert.equal(await warned(), false);
  await page.evaluate(() => gzhEditor.undo());
  assert.equal(await warned(), true);
});

test('删除段落隐藏空占位，撤销恢复显示，服务重载的空段同样隐藏', async t => {
  const page = await fixture(t);
  await select(page, 'b3', 0, 5); await page.keyboard.press('Backspace');
  assert.equal(await page.locator('[data-gzh-edit-id="b3"]').getAttribute('data-gzh-edit-empty'), '1');
  assert.equal(await page.locator('[data-gzh-edit-id="b3"]').isVisible(), false);
  await page.evaluate(() => gzhEditor.undo());
  assert.equal(await page.locator('[data-gzh-edit-id="b3"]').getAttribute('data-gzh-edit-empty'), null);
  assert.equal(await page.locator('[data-gzh-edit-id="b3"]').isVisible(), true);
  const reloaded = await fixture(t, false, true, true);
  assert.equal(await reloaded.locator('[data-gzh-edit-id="b3"]').isVisible(), false);
});

test('跨段删除仅删除选区文字，保留中间图片', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 8, 2, 'b3');
  await page.keyboard.press('Backspace');
  const pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾');
  assert.equal(pack.blocks[1].runs.map(x => x.text).join(''), '段正文');
  assert.deepEqual(await page.locator('img').evaluateAll(nodes => nodes.map(x => x.src)), baseline.images);
});

test('跨段输入替换选区，整个操作可一次撤销', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 8, 2, 'b3');
  await page.keyboard.insertText('替换');
  let pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾替换');
  assert.equal(pack.blocks[1].runs.map(x => x.text).join(''), '段正文');
  await page.evaluate(() => gzhEditor.undo());
  pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾删除');
  assert.equal(pack.blocks[1].runs.map(x => x.text).join(''), '下一段正文');
});

test('标题整块键盘删除仍需用整行操作，H3 序号可修改', async t => {
  const page = await fixture(t);
  await select(page, 'b2', 0, 7);
  await page.keyboard.press('Backspace');
  assert.equal(await page.locator('h3').innerText(), baseline.headings[0]);
  await select(page, 'b2', 0, 1);
  await page.keyboard.insertText('2');
  assert.equal(await page.locator('h3').innerText(), '2. 编号标题');
});

test('H4 微标题可编辑，首开保留原始排版外观与链接嵌套', async t => {
  const page = await fixture(t, true);
  assert.equal(await page.locator('h4').getAttribute('contenteditable'), 'true');
  assert.equal(await page.locator('h4').evaluate(el => getComputedStyle(el).fontSize), '16px');
  assert.equal(await page.locator('[data-original-look]').evaluate(el => getComputedStyle(el).fontSize), '19px');
  assert.equal(await page.locator('p a strong').count(), 1);
  assert.equal((await exported(page)).blocks[0].runs.find(x => x.href).red, true);
  await select(page, 'b1', 2, 6);
  await page.getByRole('button', { name: '取消标红', exact: true }).click();
  await page.getByRole('button', { name: '取消加粗', exact: true }).click();
  assert.equal(await page.locator('p a').evaluate(el => getComputedStyle(el).color), 'rgb(87, 107, 149)');
  assert.equal(await page.locator('p a').evaluate(el => getComputedStyle(el).fontWeight), '400');
  assert.match(await page.locator('p a').evaluate(el => getComputedStyle(el).textDecorationLine), /underline/);
});

test('选区离开文章后不会把格式误用到旧选区', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 0, 2);
  await page.evaluate(() => {
    const range = document.createRange(); range.selectNodeContents(document.getElementById('gzh-editor-status'));
    const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
    gzhEditor.applyFormat('red', true);
  });
  assert.equal((await exported(page)).blocks[0].runs[0].red, false);
});

test('换行在预览和移除编辑属性的复制内容中都可见', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 8, 10);
  await page.keyboard.insertText('甲\n乙');
  await page.evaluate(() => gzhEditor.setEditing(false));
  const text = await page.locator('[data-gzh-edit-id="b1"]').innerText();
  assert.match(text, /甲\n乙/);
  const copiedText = await page.locator('[data-gzh-edit-id="b1"]').evaluate(el => {
    const copy = el.cloneNode(true); copy.removeAttribute('data-gzh-edit-id'); copy.removeAttribute('contenteditable');
    copy.querySelectorAll('[data-gzh-run]').forEach(node => node.removeAttribute('data-gzh-run'));
    document.body.appendChild(copy); const result = copy.innerText; copy.remove(); return result;
  });
  assert.match(copiedText, /甲\n乙/);
});

for (const eventName of ['input', 'compositionend']) {
  test(`撤销后 ${eventName} 使用当前文字状态，不回灌旧闭包`, async t => {
    const page = await fixture(t);
    await select(page, 'b1', 10, 10);
    await page.keyboard.insertText('A');
    await page.evaluate(() => gzhEditor.undo());
    await page.locator('[data-gzh-edit-id="b1"]').evaluate((el, eventName) => {
      const leaf = el.lastElementChild; leaf.appendChild(document.createTextNode('B'));
      el.dispatchEvent(new Event(eventName, { bubbles: true }));
    }, eventName);
    const pack = await exported(page);
    assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾删除B');
    assert.equal(pack.blocks[0].runs.find(x => x.href).href, baseline.blocks[0].runs[1].href);
  });
}

test('Chromium 中文组合输入在撤销后提交，保留文本和链接样式', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 10, 10);
  await page.keyboard.insertText('A');
  await page.evaluate(() => gzhEditor.undo());
  await select(page, 'b1', 10, 10);
  const session = await page.context().newCDPSession(page);
  await session.send('Input.imeSetComposition', { text: 'ni', selectionStart: 2, selectionEnd: 2 });
  await session.send('Input.imeSetComposition', { text: '你', selectionStart: 1, selectionEnd: 1 });
  await session.send('Input.insertText', { text: '你好' });
  const pack = await exported(page);
  assert.equal(pack.blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾删除你好');
  assert.equal(pack.blocks[0].runs.find(x => x.href).red, true);
  await page.evaluate(() => gzhEditor.undo());
  assert.equal((await exported(page)).blocks[0].runs.map(x => x.text).join(''), '开头链接文字结尾删除');
});

test('h2 映射到 P 时序号可修改，整块键盘删除仍需用整行操作', async t => {
  const page = await fixture(t);
  const number = page.locator('[data-gzh-edit-id="b5"][data-gzh-edit-part="number"]');
  await number.selectText();
  await page.keyboard.insertText('03');
  assert.equal(await number.innerText(), '03');
  const title = page.locator('[data-gzh-edit-id="b5"]:not([data-gzh-edit-part="number"])');
  await title.selectText();
  await page.keyboard.press('Backspace');
  assert.equal(await title.innerText(), '2. 一级标题');
});

test('修改链接后复制内容的所有中文文字均保留 span leaf 包裹', async t => {
  const page = await fixture(t);
  await select(page, 'b1', 2, 6);
  await page.getByRole('button', { name: '取消标红', exact: true }).click();
  const result = await page.locator('#gzh-content').evaluate(el => {
    const copy = el.cloneNode(true);
    copy.querySelectorAll('*').forEach(node => {
      node.removeAttribute('contenteditable'); node.removeAttribute('spellcheck');
      [...node.attributes].filter(attr => attr.name.startsWith('data-gzh-')).forEach(attr => node.removeAttribute(attr.name));
    });
    const walker = document.createTreeWalker(copy, NodeFilter.SHOW_TEXT);
    const unwrapped = []; let node;
    while ((node = walker.nextNode())) {
      if (/[\u3400-\u9fff]/.test(node.data) && !node.parentElement.closest('span[leaf]')) unwrapped.push(node.data);
    }
    return { unwrapped, link: copy.querySelector('a').outerHTML };
  });
  assert.deepEqual(result.unwrapped, []);
  assert.match(result.link, /<span[^>]*leaf=""[^>]*>链接文字<\/span>/);
  assert.doesNotMatch(result.link, /data-gzh-|contenteditable/);
  const linkRun = (await exported(page)).blocks[0].runs.find(run => run.href);
  assert.equal(linkRun.href, baseline.blocks[0].runs[1].href);
  assert.equal(linkRun.red, false);
  assert.equal(linkRun.bold, true);
});
