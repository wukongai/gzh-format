/* 独立本地服务：改稿→保存草稿→撤销/重做→再次保存→重开与同步预检。 */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync, spawn} = require('node:child_process');
const {chromium} = require('playwright');
const scripts = path.resolve(__dirname, '../scripts');

function python(args) {
  const result = spawnSync(process.env.GZH_TEST_PYTHON || 'python3', args, {encoding:'utf8'});
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return result.stdout;
}

for (const viewportWidth of [1100, 390, 320]) {
test(`手机阅读宽度在 ${viewportWidth}px 窗口下直接编辑保存、撤销重做和重开均保真`, async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gzh-edit-e2e-'));
  let browser, service;
  try {
    const md = path.join(root, 'article.md'), html = path.join(root, 'article.html');
    const preview = path.join(root, 'article_预览.html');
    const manifest = path.join(root, 'article.gzh-edit-manifest.json');
    const original = '---\ntitle: 独立验收稿\nrelated: ["[[测试]]"]\n---\n\n# 独立验收稿\n\n## 一、编辑测试\n\n'
      + Array.from({length:11},(_,i)=>`### ${i+1}. 保留编号\n\n原始正文${i+1}，包含 **加粗** 和 [链接](https://example.invalid/read)。\n\n`).join('')
      + Array.from({length:16},(_,i)=>`![图${i}](https://example.invalid/${i}.png)\n\n`).join('')
      + '> 引用第一行\n> 引用第二行\n\n第一，微标题。\n\n- 列表甲\n- 列表乙\n';
    fs.writeFileSync(md, original);
    python([path.join(scripts, 'render_markdown.py'), md, html]);
    python([path.join(scripts, 'wrap_preview.py'), html, '--editable', '--source-md', md]);
    const readyPath=path.join(root,'service-ready.json');
    service=spawn(process.env.GZH_TEST_PYTHON || 'python3',[path.join(scripts,'serve_preview.py'),'--manifest',manifest,'--ready-file',readyPath],{stdio:['ignore','pipe','pipe']});
    let diagnostics='';service.stderr.on('data',chunk=>{diagnostics+=chunk;});
    for(let attempt=0;attempt<100&&!fs.existsSync(readyPath)&&service.exitCode===null;attempt++)await new Promise(resolve=>setTimeout(resolve,50));
    assert.ok(fs.existsSync(readyPath),diagnostics || '本机保存服务没有就绪');
    const ready=JSON.parse(fs.readFileSync(readyPath,'utf8'));
    const options={headless:true};
    if(process.env.GZH_TEST_BROWSER) options.executablePath=process.env.GZH_TEST_BROWSER;
    browser=await chromium.launch(options);
    const page=await browser.newPage({acceptDownloads:true, viewport:{width:viewportWidth,height:900}});
    page.setDefaultTimeout(7000);
    await page.route(/^https?:/, route=>new URL(route.request().url()).origin===ready.origin?route.continue():route.abort());
    const errors=[]; page.on('pageerror',error=>errors.push(error.message));
    await page.goto(ready.url);
    assert.equal(await page.evaluate(()=>Boolean(window.gzhEditor)),true);
    // 桌面默认仍按手机宽度排版；窄于参考宽度时随窗口收缩，不缩放字号。
    const bodyWidth = Math.min(390, viewportWidth);
    assert.equal(Math.round((await page.locator('#gzh-content').boundingBox()).width),bodyWidth);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),viewportWidth);
    assert.equal(await page.getByRole('button',{name:'保存草稿',exact:true}).isEnabled(),true);
    // 显式只读查看与继续编辑都留在同一手机宽度页面。
    await page.getByRole('button',{name:'切换为预览',exact:true}).click();
    assert.equal(await page.locator('#gzh-content [contenteditable="true"]').count(),0);
    assert.equal(Math.round((await page.locator('#gzh-content').boundingBox()).width),bodyWidth);
    await page.getByRole('button',{name:'继续编辑',exact:true}).click();
    assert.ok(await page.locator('#gzh-content [contenteditable="true"]').count()>0);
    assert.equal(await page.getByRole('button',{name:/导出|另存/}).count(),0);
    const initial=await page.evaluate(()=>JSON.parse(document.getElementById('gzh-edit-data').textContent));
    const paragraphs=initial.blocks.filter(b=>b.kind==='paragraph');
    async function select(id,start,end){
      await page.evaluate(({id,start,end})=>{
        const el=document.querySelector(`[data-gzh-edit-id="${id}"]`),nodes=[];
        const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);while(walker.nextNode())nodes.push(walker.currentNode);
        function point(n){for(const node of nodes){if(n<=node.length)return[node,n];n-=node.length;}return[el,el.childNodes.length];}
        el.focus();const range=document.createRange();range.setStart(...point(start));range.setEnd(...point(end));
        getSelection().removeAllRanges();getSelection().addRange(range);
      },{id,start,end});
    }
    const text='人工保留\n独立红字';
    await page.getByLabel('文章标题').fill('手机预览中的新标题');
    await select(paragraphs[0].id,0,paragraphs[0].runs.map(r=>r.text).join('').length);
    await page.keyboard.insertText(text);
    await select(paragraphs[0].id,0,4);
    await page.getByRole('button',{name:'加粗',exact:true}).click();
    await page.getByRole('button',{name:'取消标红',exact:true}).click();
    await select(paragraphs[0].id,5,9);
    await page.getByRole('button',{name:'标红',exact:true}).click();
    await page.getByRole('button',{name:'取消加粗',exact:true}).click();
    await select(paragraphs[1].id,0,paragraphs[1].runs.map(r=>r.text).join('').length);
    await page.keyboard.press('Backspace');
    assert.equal(fs.readFileSync(md,'utf8'),original);
    await page.getByRole('button',{name:'保存草稿',exact:true}).click();
    await page.waitForFunction(()=>!gzhEditor.isDirty());
    assert.match(await page.locator('#gzh-editor-status').innerText(),/已保存/);
    let state=JSON.parse(fs.readFileSync(manifest,'utf8'));
    assert.equal(state.revision,1);
    assert.match(fs.readFileSync(md,'utf8'),/手机预览中的新标题/);
    const revisionRoot=path.join(root,'.gzh-edits',state.article_id);
    const backup=path.join(revisionRoot,fs.readdirSync(revisionRoot)[0],'source.md');
    assert.equal(fs.readFileSync(backup,'utf8'),original);
    const content=fs.readFileSync(html,'utf8');
    assert.equal((content.match(/<img /g)||[]).length,16);
    assert.equal((content.match(/<h3 /g)||[]).length,11);
    assert.ok(!content.includes('原始正文2，')); assert.ok(content.includes('人工保留'));
    assert.ok(content.includes('color:#DC2626;font-weight:400'));
    assert.ok(!/contenteditable|data-gzh-edit|<script|<button/.test(content));
    assert.equal(JSON.parse(python([path.join(scripts,'preflight_edit.py'),'--manifest',manifest])).status,'saved');
    // 保存不清空历史：撤销已落盘的删段，再保存恢复；重做后再保存删除。
    await page.getByRole('button',{name:'撤销',exact:true}).click();
    assert.equal(await page.evaluate(()=>gzhEditor.isDirty()),true);
    await page.getByRole('button',{name:'保存草稿',exact:true}).click();
    await page.waitForFunction(()=>!gzhEditor.isDirty());
    assert.ok(fs.readFileSync(html,'utf8').includes('原始正文2，'));
    assert.equal(JSON.parse(fs.readFileSync(manifest,'utf8')).revision,2);
    await page.getByRole('button',{name:'重做',exact:true}).click();
    await page.getByRole('button',{name:'保存草稿',exact:true}).click();
    await page.waitForFunction(()=>!gzhEditor.isDirty());
    assert.ok(!fs.readFileSync(html,'utf8').includes('原始正文2，'));
    await page.reload();
    const reloaded=await page.evaluate(()=>gzhEditor.exportPackage());
    assert.equal(reloaded.revision,3);
    assert.equal(await page.getByLabel('文章标题').inputValue(),'手机预览中的新标题');
    assert.equal(Math.round((await page.locator('#gzh-content').boundingBox()).width),bodyWidth);
    const kept=reloaded.blocks.find(b=>b.runs.map(r=>r.text).join('')===text);
    assert.ok(kept); assert.equal(kept.runs.find(r=>r.text.includes('人工保留')).bold,true);
    assert.equal(errors.length,0,errors.join('\n'));
    assert.equal(await page.evaluate(()=>gzhEditor.isDirty()),false);
  } finally {
    if(browser)await browser.close();
    if(service&&service.exitCode===null){service.kill();await new Promise(resolve=>service.once('close',resolve));}
    fs.rmSync(root,{recursive:true,force:true});
  }
});
}

test('只读静态预览也默认手机宽度，缩窄时适配且复制正文不变', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'gzh-mobile-readonly-'));
  let browser;
  try {
    const md=path.join(root,'article.md'), html=path.join(root,'article.html');
    const preview=path.join(root,'preview.html');
    fs.writeFileSync(md,'# 手机预览测试\n\n'+ '同一段正文用手机宽度检查阅读长度。'.repeat(12)+'\n');
    python([path.join(scripts,'render_markdown.py'),md,html]);
    python([path.join(scripts,'wrap_preview.py'),html,preview,'--source-md',md]);
    const options={headless:true};
    if(process.env.GZH_TEST_BROWSER) options.executablePath=process.env.GZH_TEST_BROWSER;
    browser=await chromium.launch(options);
    const page=await browser.newPage();
    await page.goto(require('node:url').pathToFileURL(preview).href);
    for(const width of [1100,390,320]) {
      await page.setViewportSize({width,height:900});
      assert.equal(Math.round((await page.locator('#gzh-content').boundingBox()).width),Math.min(390,width));
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
      assert.equal(await page.locator('#gzh-title').getAttribute('readonly'),'');
      assert.equal(await page.locator('[contenteditable="true"]').count(),0);
    }
    // 仅预览外壳改变宽度；复制区域的正文不混入手机标记、按钮或脚本。
    assert.equal(await page.locator('#gzh-content').innerHTML(), '\n'+fs.readFileSync(html,'utf8')+'\n  ');
  } finally {
    if(browser)await browser.close();
    fs.rmSync(root,{recursive:true,force:true});
  }
});
