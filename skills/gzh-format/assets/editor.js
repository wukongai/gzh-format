/* 共享公众号预览编辑器：受控文字 runs 通过同源本地服务真正保存草稿。 */
(function () {
  'use strict';
  var dataNode = document.getElementById('gzh-edit-data');
  var content = document.getElementById('gzh-content');
  var toolbar = document.getElementById('gzh-editor-toolbar');
  var titleInput = document.getElementById('gzh-title');
  if (!dataNode || !content || !toolbar) return;

  var baseline;
  try { baseline = JSON.parse(dataNode.textContent); } catch (error) { toolbar.textContent = '编辑基线无法读取，已关闭编辑。'; return; }
  if (baseline.schema !== 'gzh-edit/v1' || !Array.isArray(baseline.blocks)) {
    toolbar.textContent = '编辑基线版本不支持，已关闭编辑。'; return;
  }
  var clone = function (value) { return JSON.parse(JSON.stringify(value)); };
  var markNames = ['code', 'underline', 'strike', 'highlight'];
  var AUTO_SAVE_INTERVAL_MS = 2 * 60 * 1000;
  var editing = true;
  var blocks = clone(baseline.blocks);
  var title = typeof baseline.title === 'string' ? baseline.title : titleInput ? titleInput.value : '';
  var titleEditable = titleInput && !titleInput.readOnly;
  if (titleInput) titleInput.value = title;
  var elements = new Map();
  var partElements = new Map();
  var originalWrappers = new WeakMap();
  var savedSelection = null;
  // 工具条操作需要一个明确的当前块，即使用户刚点击了块但还没有选中文字。
  var activeBlockId = null;
  var history = [];
  var historyIndex = -1;
  var composing = false;
  var status;
  var undoButton;
  var redoButton;
  var modeButton;
  var saveButton;
  var autoSaveNotice;
  var saving = false;
  var savedOnce = false;
  var unconfirmedSubmission = null;
  var lastSavedAt = typeof baseline.saved_at === 'string' ? baseline.saved_at : null;

  function message(text) { status.textContent = text; }
  function saveBridge() {
    var bridge = baseline.save_bridge;
    if (!bridge || typeof bridge.save_url !== 'string' || !bridge.save_url || typeof bridge.session_token !== 'string' || !bridge.session_token || !/^https?:$/.test(window.location.protocol)) return null;
    try {
      var url = new URL(bridge.save_url, window.location.href);
      if (url.origin !== window.location.origin || !/^https?:$/.test(url.protocol)) return null;
      return { url: url.href, sessionToken: bridge.session_token };
    } catch (error) { return null; }
  }
  function updateAutoSaveNotice() {
    if (!autoSaveNotice) return;
    var text = saveBridge() ? '自动保存：每 2 分钟' : '自动保存：需本机服务';
    if (lastSavedAt) {
      var date = new Date(lastSavedAt);
      if (!Number.isNaN(date.getTime())) text += '｜最近保存 ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    autoSaveNotice.textContent = text;
  }
  function updateSaveButton() { saveButton.disabled = saving || !saveBridge(); saveButton.textContent = saving ? '正在保存…' : '保存草稿'; }
  function stateMessage(prefix) {
    var dirty = composing || Boolean(unconfirmedSubmission) || stateKey() !== initialKey;
    if (!saveBridge()) { message((dirty ? '有未保存的修改；' : '') + '请从本地保存服务打开，才能保存草稿。'); return; }
    if (saving) { message('正在保存草稿；你可以继续编辑。'); return; }
    if (unconfirmedSubmission) { message('上次保存结果尚未确认，请再次保存草稿；当前修改仍保留在页面。'); return; }
    message((prefix || '') + (dirty ? '还有未保存的修改。' : savedOnce ? '已保存草稿。' : '当前没有未保存的修改，可直接编辑并保存。'));
  }
  function canonicalRun(run) {
    return { text: run.text, red: run.red === true, bold: run.bold === true,
      href: run.href || '', marks: (run.marks || []).filter(function (mark) { return markNames.indexOf(mark) >= 0; }) };
  }
  function styleKey(run) { return JSON.stringify([run.red, run.bold, run.href, run.marks]); }
  function compact(runs) {
    var result = [];
    runs.forEach(function (run) {
      if (!run.text) return;
      var next = canonicalRun(run);
      var last = result[result.length - 1];
      if (last && styleKey(last) === styleKey(next)) last.text += next.text;
      else result.push(next);
    });
    return result;
  }
  function blockText(block) { return block.runs.map(function (run) { return run.text; }).join(''); }
  function normalizeNumber(value) {
    return String(value || '').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 40);
  }
  function allRuns() {
    return blocks.map(function (block) {
      var output = { id: block.id, runs: clone(block.runs) };
      if (block.kind === 'h2') output.number = normalizeNumber(block.number);
      return output;
    });
  }
  function stateKey() { return JSON.stringify({ title: title, blocks: allRuns() }); }
  var initialKey;
  try {
    blocks.forEach(function (block) {
      if (typeof block.id !== 'string' || elements.has(block.id) || !Array.isArray(block.runs)) throw new Error('文字块基线不完整');
      var matches = Array.from(content.querySelectorAll('[data-gzh-edit-id]')).filter(function (el) { return el.getAttribute('data-gzh-edit-id') === block.id; });
      var primaryMatches = matches.filter(function (el) { return el.getAttribute('data-gzh-edit-part') !== 'number'; });
      if (primaryMatches.length !== 1 || !/^(P|H3|H4)$/.test(primaryMatches[0].tagName)) throw new Error('文字块映射不完整');
      var numberParts = matches.filter(function (el) { return el.getAttribute('data-gzh-edit-part') === 'number'; });
      if (block.kind === 'h2') {
        if (numberParts.length > 1) throw new Error('章节序号映射不完整');
        if (typeof block.number !== 'string') block.number = numberParts.length ? normalizeNumber(numberParts[0].textContent) : '';
        block.number = normalizeNumber(block.number);
      }
      block.runs.forEach(function (run) {
        if (typeof run.text !== 'string' || (run.href && !/^(https?:|mailto:)/i.test(run.href))) throw new Error('文字块基线格式不支持');
      });
      block.runs = compact(block.runs);
      elements.set(block.id, primaryMatches[0]);
      partElements.set(block.id, numberParts);
    });
    initialKey = stateKey();
  } catch (error) { toolbar.textContent = error.message + '，已关闭编辑。'; return; }

  function renderNumberPart(block) {
    (partElements.get(block.id) || []).forEach(function (part) {
      var leaf = part.querySelector('[leaf]') || part;
      leaf.textContent = normalizeNumber(block.number);
      part.setAttribute('contenteditable', editing ? 'true' : 'false');
      part.setAttribute('spellcheck', 'false');
      part.style.display = block.runs.length && (normalizeNumber(block.number) || editing) ? '' : 'none';
      if (block.runs.length && normalizeNumber(block.number)) part.removeAttribute('data-gzh-edit-empty');
      else part.setAttribute('data-gzh-edit-empty', '1');
    });
  }
  function readNumberPart(block) {
    var part = (partElements.get(block.id) || [])[0];
    if (!part) return normalizeNumber(block.number);
    var next = normalizeNumber(part.textContent);
    block.number = next;
    if (part.textContent !== next) renderNumberPart(block);
    return next;
  }
  function renderBlock(block) {
    // undo/redo 会替换状态数组；事件只保留块身份，重绘必须读取当前版本。
    block = blocks.find(function (current) { return current.id === block.id; });
    var el = elements.get(block.id);
    var fragment = document.createDocumentFragment();
    block.runs.forEach(function (run, index) {
      var leaf = document.createElement(run.href ? 'a' : 'span');
      leaf.setAttribute('data-gzh-run', String(index));
      leaf.setAttribute('leaf', '');
      if (run.href) { leaf.setAttribute('href', run.href); leaf.setAttribute('target', '_blank'); }
      // 显式 normal 可解除既有粗体；红色和粗体始终由两个独立状态控制。
      leaf.style.fontWeight = run.bold ? '800' : '400';
      leaf.style.color = run.red ? '#DC2626' : run.href ? '#576b95' : '#4d4f46';
      if (run.marks.indexOf('underline') >= 0 || run.marks.indexOf('strike') >= 0) {
        leaf.style.textDecoration = [run.marks.indexOf('underline') >= 0 ? 'underline' : '', run.marks.indexOf('strike') >= 0 ? 'line-through' : ''].filter(Boolean).join(' ');
      }
      if (run.href) leaf.style.textDecoration = (leaf.style.textDecoration || '') + ' underline';
      // 换行随可复制内容保留，不能只依赖预览外壳的编辑态 CSS。
      if (run.text.indexOf('\n') >= 0) leaf.style.whiteSpace = 'pre-wrap';
      if (run.marks.indexOf('code') >= 0) {
        leaf.style.fontFamily = 'ui-monospace,Menlo,Monaco,Consolas,monospace'; leaf.style.backgroundColor = '#eeefe9';
        leaf.style.padding = '2px 6px'; leaf.style.borderRadius = '4px'; leaf.style.fontSize = '13px'; leaf.style.border = '1px solid #b6b7af';
      } else if (run.marks.indexOf('highlight') >= 0) {
        leaf.style.backgroundColor = '#eeefe9'; leaf.style.padding = '1px 5px'; leaf.style.borderRadius = '4px'; leaf.style.border = '1px solid #bfc1b7';
      }
      if (run.href) {
        // 公众号校验只认可 span[leaf]，链接本身不能替代文字叶节点。
        leaf.removeAttribute('leaf');
        var linkText = document.createElement('span');
        linkText.setAttribute('leaf', ''); linkText.setAttribute('data-gzh-run', String(index));
        linkText.textContent = run.text; leaf.appendChild(linkText);
      } else leaf.textContent = run.text;
      fragment.appendChild(leaf);
    });
    el.replaceChildren(fragment);
    el.setAttribute('contenteditable', editing ? 'true' : 'false');
    el.setAttribute('spellcheck', 'false');
    if (block.runs.length) el.removeAttribute('data-gzh-edit-empty');
    else el.setAttribute('data-gzh-edit-empty', '1');
    renderNumberPart(block);
  }
  function renderAll() { blocks.forEach(renderBlock); }
  function prepareBlock(block) {
    var el = elements.get(block.id);
    if (el.textContent !== blockText(block) || !el.childNodes.length) { renderBlock(block); return; }
    // 首开保留 renderer 的全部外观，只为原文字加无样式的受控映射。
    Array.from(el.querySelectorAll('*')).forEach(function (wrapper) {
      originalWrappers.set(wrapper, { href: wrapper.tagName === 'A' ? wrapper.getAttribute('href') : null });
    });
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); var texts = []; var node;
    while ((node = walker.nextNode())) texts.push(node);
    var runIndex = 0; var runOffset = 0;
    texts.forEach(function (textNode) {
      var fragment = document.createDocumentFragment(); var local = 0;
      while (local < textNode.data.length) {
        while (runIndex < block.runs.length && runOffset >= block.runs[runIndex].text.length) { runIndex += 1; runOffset = 0; }
        if (!block.runs[runIndex]) throw new Error('文字块映射不完整');
        var length = Math.min(textNode.data.length - local, block.runs[runIndex].text.length - runOffset);
        var span = document.createElement('span'); span.setAttribute('data-gzh-run', String(runIndex));
        span.textContent = textNode.data.slice(local, local + length); fragment.appendChild(span); local += length; runOffset += length;
      }
      textNode.replaceWith(fragment);
    });
    el.setAttribute('contenteditable', editing ? 'true' : 'false'); el.setAttribute('spellcheck', 'false');
    if (block.runs.length) el.removeAttribute('data-gzh-edit-empty');
    else el.setAttribute('data-gzh-edit-empty', '1');
    renderNumberPart(block);
  }

  function readBlock(block) {
    var el = elements.get(block.id);
    var runs = [];
    var plain = { text: '', red: false, bold: false, href: '', marks: [] };
    function visit(node, inherited) {
      if (node.nodeType === Node.TEXT_NODE) { var run = canonicalRun(inherited); run.text = node.data; runs.push(run); return; }
      if (node.nodeType !== Node.ELEMENT_NODE) throw new Error('发现不支持的编辑结构，请撤销后重试');
      if (node.tagName === 'BR') { var newline = canonicalRun(inherited); newline.text = '\n'; runs.push(newline); return; }
      if (originalWrappers.has(node)) {
        if (node.tagName === 'A' && originalWrappers.get(node).href !== node.getAttribute('href')) throw new Error('链接结构已变化，请撤销后重试');
        Array.from(node.childNodes).forEach(function (child) { visit(child, inherited); }); return;
      }
      if (!/^(SPAN|A)$/.test(node.tagName)) throw new Error('发现不支持的编辑结构，请撤销后重试');
      var token = node.getAttribute('data-gzh-run');
      if (token === null || !/^\d+$/.test(token) || !block.runs[Number(token)]) throw new Error('发现未注册的文字格式，请撤销后重试');
      var source = block.runs[Number(token)];
      if ((node.tagName === 'A' && (!source.href || node.getAttribute('href') !== source.href))) throw new Error('链接结构已变化，请撤销后重试');
      Array.from(node.childNodes).forEach(function (child) { visit(child, source); });
    }
    Array.from(el.childNodes).forEach(function (child) { visit(child, plain); });
    return compact(runs);
  }
  function syncDOM() {
    // 先验证全部块再修改状态，避免一个坏节点造成半篇提交。
    var next = blocks.map(function (block) { return readBlock(block); });
    blocks.forEach(function (block, index) { protectHeading(block, next[index]); });
    blocks.forEach(function (block, index) { block.runs = next[index]; });
    blocks.forEach(function (block) { if (block.kind === 'h2') readNumberPart(block); });
    if (titleInput) title = titleInput.value;
  }
  function protectHeading(block, runs) {
    if (['h2', 'h3', 'micro'].indexOf(block.kind) < 0 && !/^H[34]$/.test(elements.get(block.id).tagName)) return;
    var original = baseline.blocks.find(function (candidate) { return candidate.id === block.id; }).runs.map(function (run) { return run.text; }).join('');
    var nextText = runs.map(function (run) { return run.text; }).join('');
    // 显式删除整行后，块自身已经是空状态，后续同步允许继续保持空；
    // 普通键盘删除仍会从非空旧状态变成空，继续阻断以避免误删标题。
    if (!nextText.trim() && block.runs.length) throw new Error('标题整块删除请使用“删除整行”；序号文字可以单独编辑。');
  }
  function offsetIn(el, node, offset) {
    var range = document.createRange(); range.selectNodeContents(el); range.setEnd(node, offset); return range.toString().length;
  }
  function selectionRanges() {
    var selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return [];
    var range = selection.getRangeAt(0);
    if (!content.contains(range.startContainer) || !content.contains(range.endContainer)) return [];
    var result = [];
    blocks.forEach(function (block) {
      var el = elements.get(block.id);
      if (!range.intersectsNode(el)) return;
      var start = el.contains(range.startContainer) ? offsetIn(el, range.startContainer, range.startOffset) : 0;
      var end = el.contains(range.endContainer) ? offsetIn(el, range.endContainer, range.endOffset) : blockText(block).length;
      result.push({ id: block.id, start: start, end: end });
    });
    if (result.length) activeBlockId = result[0].id;
    return result;
  }
  function rememberSelection() { var ranges = selectionRanges(); if (ranges.length) savedSelection = ranges; }
  function point(el, offset) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) { if (offset <= node.length) return [node, offset]; offset -= node.length; }
    return [el, el.childNodes.length];
  }
  function restoreSelection(ranges) {
    if (!ranges || !ranges.length) return;
    var first = ranges[0]; var last = ranges[ranges.length - 1];
    var startEl = elements.get(first.id); var endEl = elements.get(last.id);
    if (!startEl || !endEl) return;
    var range = document.createRange(); range.setStart.apply(range, point(startEl, first.start)); range.setEnd.apply(range, point(endEl, last.end));
    startEl.focus(); var selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    savedSelection = clone(ranges);
  }
  function historyButtons() { undoButton.disabled = historyIndex <= 0; redoButton.disabled = historyIndex >= history.length - 1; }
  function commit(ranges) {
    var current = stateKey();
    if (historyIndex >= 0 && history[historyIndex].key === current) return;
    history.splice(historyIndex + 1);
    history.push({ key: current, state: clone(blocks), title: title, selection: clone(ranges || []) });
    if (history.length > 100) history.shift();
    historyIndex = history.length - 1; historyButtons();
    stateMessage();
  }
  function moveHistory(direction) {
    if (historyIndex + direction < 0 || historyIndex + direction >= history.length) return false;
    historyIndex += direction; var state = history[historyIndex];
    var bodyChanged = JSON.stringify(blocks) !== JSON.stringify(state.state);
    blocks = clone(state.state); if (bodyChanged) renderAll();
    title = state.title; if (titleInput) titleInput.value = title;
    restoreSelection(state.selection); historyButtons(); stateMessage('已' + (direction < 0 ? '撤销' : '重做') + '；'); return true;
  }
  function editSlice(block, start, end, transform) {
    var cursor = 0; var output = [];
    block.runs.forEach(function (run) {
      var stop = cursor + run.text.length;
      var left = Math.max(cursor, start); var right = Math.min(stop, end);
      if (left >= right) output.push(clone(run));
      else {
        if (left > cursor) { var before = clone(run); before.text = run.text.slice(0, left - cursor); output.push(before); }
        var selected = clone(run); selected.text = run.text.slice(left - cursor, right - cursor); output.push(transform(selected));
        if (right < stop) { var after = clone(run); after.text = run.text.slice(right - cursor); output.push(after); }
      }
      cursor = stop;
    });
    block.runs = compact(output);
  }
  function applyFormat(axis, value) {
    if (!editing || (axis !== 'red' && axis !== 'bold') || typeof value !== 'boolean') return false;
    syncDOM(); var ranges = selectionRanges();
    if (!ranges.some(function (range) { return range.end > range.start; })) { message('先选择要修改的文字。'); return false; }
    ranges.forEach(function (range) {
      var block = blocks.find(function (candidate) { return candidate.id === range.id; });
      editSlice(block, range.start, range.end, function (run) { run[axis] = value; return run; }); renderBlock(block);
    });
    restoreSelection(ranges); commit(ranges); return true;
  }
  function deleteWholeBlock() {
    if (!editing) return false;
    syncDOM();
    var ranges = selectionRanges();
    // 即使选区跨过多个块，也只删除当前活动块，避免把相邻正文一起清空。
    var id = activeBlockId || (ranges.length ? ranges[0].id : '');
    var target = id ? blocks.find(function (block) { return block.id === id; }) : null;
    if (!target) { message('先点击要删除的正文或标题块。'); return false; }
    target.runs = [];
    renderBlock(target);
    var caret = [{ id: target.id, start: 0, end: 0 }];
    restoreSelection(caret); commit(caret); message('已删除整行；可用撤销恢复。'); return true;
  }
  function insertLineBreak(block, offset) {
    var cursor = 0; var inserted = false; var output = [];
    block.runs.forEach(function (run) {
      var stop = cursor + run.text.length;
      if (!inserted && offset >= cursor && offset <= stop) {
        var local = offset - cursor;
        var before = clone(run); before.text = run.text.slice(0, local);
        var after = clone(run); after.text = run.text.slice(local);
        if (before.text) output.push(before);
        var newline = canonicalRun(run); newline.text = '\n'; newline.href = '';
        output.push(newline);
        if (after.text) output.push(after);
        inserted = true;
      } else output.push(clone(run));
      cursor = stop;
    });
    if (!inserted) {
      var fallback = canonicalRun(block.runs[block.runs.length - 1]);
      fallback.text = '\n'; fallback.href = '';
      output.push(fallback);
    }
    block.runs = compact(output);
  }
  function addWholeLine() {
    if (!editing) return false;
    syncDOM();
    var ranges = selectionRanges();
    var id = activeBlockId || (ranges.length ? ranges[0].id : '');
    var block = id ? blocks.find(function (candidate) { return candidate.id === id; }) : null;
    if (!block) { message('先点击要添加内容的正文或标题块。'); return false; }
    var text = blockText(block);
    if (!text) { message('空块无需添加换行，请先输入文字。'); return false; }
    var selected = ranges.find(function (range) { return range.id === block.id; });
    var insertAt = selected ? selected.end : text.length;
    insertLineBreak(block, insertAt);
    renderBlock(block);
    var caret = [{ id: block.id, start: insertAt + 1, end: insertAt + 1 }];
    restoreSelection(caret); commit(caret); message('已添加一行；文字样式保持不变。'); return true;
  }
  function replaceSelection(text, deleteDirection) {
    var ranges = selectionRanges();
    if (!ranges.length) return false;
    syncDOM(); var firstStart = ranges[0].start;
    var changes = ranges.map(function (selected, rangeIndex) {
      var block = blocks.find(function (candidate) { return candidate.id === selected.id; });
      var start = selected.start; var end = selected.end; var full = blockText(block); var inserted = rangeIndex === 0 ? text : '';
      if (ranges.length === 1 && start === end && deleteDirection) {
        if (deleteDirection < 0 && start > 0) start -= /[\uDC00-\uDFFF]/.test(full.charAt(start - 1)) && start > 1 ? 2 : 1;
        if (deleteDirection > 0 && end < full.length) end += /[\uD800-\uDBFF]/.test(full.charAt(end)) && end + 1 < full.length ? 2 : 1;
      }
      if (rangeIndex === 0) firstStart = start;
      var cursor = 0; var prefix = []; var suffix = []; var inherited = canonicalRun({ text: '', red: false, bold: false, href: '', marks: [] });
      block.runs.forEach(function (run) {
        var stop = cursor + run.text.length;
        if (start >= cursor && start <= stop) inherited = canonicalRun(run);
        if (cursor < start) { var left = clone(run); left.text = run.text.slice(0, Math.min(run.text.length, start - cursor)); prefix.push(left); }
        if (stop > end) { var right = clone(run); right.text = run.text.slice(Math.max(0, end - cursor)); suffix.push(right); }
        cursor = stop;
      });
      inherited.text = inserted; var runs = compact(prefix.concat(inserted ? [inherited] : [], suffix));
      protectHeading(block, runs);
      return { block: block, runs: runs };
    });
    changes.forEach(function (change) { change.block.runs = change.runs; renderBlock(change.block); });
    var caret = [{ id: ranges[0].id, start: firstStart + text.length, end: firstStart + text.length }]; restoreSelection(caret); commit(caret); return true;
  }
  function recover(error, block) { renderBlock(block); message(error.message); }
  function setEditing(value) {
    syncDOM(); editing = Boolean(value); elements.forEach(function (el) { el.setAttribute('contenteditable', editing ? 'true' : 'false'); });
    partElements.forEach(function (parts, id) {
      parts.forEach(function (part) { part.setAttribute('contenteditable', editing ? 'true' : 'false'); });
      var block = blocks.find(function (candidate) { return candidate.id === id; });
      if (block) renderNumberPart(block);
    });
    if (titleInput) titleInput.readOnly = !editing || !titleEditable;
    modeButton.textContent = editing ? '切换为预览' : '继续编辑'; toolbar.setAttribute('data-editing', String(editing));
    stateMessage(editing ? '' : '预览模式；'); return editing;
  }
  function exportPackage() {
    syncDOM(); var output = clone(baseline); delete output.save_bridge;
    if (titleInput || typeof baseline.title === 'string') {
      if (!title.trim() || title.length > 2000 || /[\x00-\x1f\x7f-\x9f\u2028\u2029]/.test(title)) throw new Error('标题必须为非空单行纯文字，不能含控制字符。');
      output.title = title;
    }
    output.blocks = allRuns(); output.saved_at = new Date().toISOString(); return output;
  }
  async function submitDraft(submission, bridge) {
    // 原样缓存含 saved_at 的提交；网络中断不能判定服务端是否已落盘。
    unconfirmedSubmission = submission;
    var response = await window.fetch(bridge.url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', mode: 'same-origin', redirect: 'error',
      body: JSON.stringify({ session_token: bridge.sessionToken, package: submission.payload })
    });
    // 4xx 是明确拒绝；5xx、坏 JSON 或缺失成功基线仍需幂等确认。
    if (response.status >= 400 && response.status < 500) unconfirmedSubmission = null;
    var result = await response.json();
    if (!response.ok || (result.status !== 'saved' && result.status !== 'already-imported')) throw new Error(result.error || result.message || '本地保存服务返回 HTTP ' + response.status);
    var next = result.package;
    if (!next || next.schema !== baseline.schema || next.article_id !== baseline.article_id || !Number.isInteger(next.revision) || next.revision < baseline.revision ||
        (typeof submission.payload.title === 'string' && next.title !== submission.payload.title) ||
        typeof next.source_sha256 !== 'string' || typeof next.html_sha256 !== 'string' || !Array.isArray(next.images) || !Array.isArray(next.headings) ||
        !Array.isArray(next.blocks) || next.blocks.length !== blocks.length || next.blocks.some(function (block, index) {
          return block.id !== blocks[index].id || !Array.isArray(block.runs) || (blocks[index].kind === 'h2' && typeof block.number !== 'string');
        })) {
      throw new Error('保存服务返回的草稿基线不完整，请保留页面并重试。');
    }
    var connection = baseline.save_bridge;
    baseline = clone(next); if (!baseline.save_bridge) baseline.save_bridge = connection;
    lastSavedAt = typeof next.saved_at === 'string' ? next.saved_at : new Date().toISOString();
    updateAutoSaveNotice();
    initialKey = submission.submittedKey; savedOnce = true; unconfirmedSubmission = null;
  }
  async function saveDraft() {
    if (saving) return false;
    var bridge = saveBridge();
    if (!bridge) { stateMessage(); return false; }
    try {
      if (composing) throw new Error('请先完成当前文字输入，再保存。');
      var recovering = Boolean(unconfirmedSubmission);
      var submission = unconfirmedSubmission;
      if (!submission) { var payload = exportPackage(); submission = { payload: payload, submittedKey: stateKey() }; }
      saving = true; updateSaveButton(); stateMessage();
      await submitDraft(submission, bridge);
      // 只有恢复未确认提交时追送一次最新内容；普通保存不冒充已保存途中输入。
      if (recovering && !composing) {
        syncDOM();
        if (stateKey() !== initialKey) {
          var latest = exportPackage();
          await submitDraft({ payload: latest, submittedKey: stateKey() }, saveBridge() || bridge);
        }
      }
      // 保存的是发出请求时的快照；保留DOM、全部历史以及请求期间的新输入。
      saving = false; updateSaveButton();
      stateMessage(composing || stateKey() !== initialKey ? '已保存提交时的草稿；' : ''); return true;
    } catch (error) {
      saving = false; updateSaveButton(); message('保存失败：' + error.message + (unconfirmedSubmission ? ' 上次提交结果尚未确认，下次保存会先重试确认。' : '') + ' 当前修改仍保留在页面。'); return false;
    }
  }
  function autoSaveTick() {
    if (saving || composing || !saveBridge()) return false;
    try {
      syncDOM();
      if (!unconfirmedSubmission && stateKey() === initialKey) return false;
    } catch (error) {
      message('自动保存等待：' + error.message + ' 当前修改仍保留在页面。');
      return false;
    }
    message('正在自动保存…');
    saveDraft().then(function (saved) {
      if (saved) stateMessage('已自动保存；');
    });
    return true;
  }
  function button(text, action, title) {
    var el = document.createElement('button'); el.type = 'button'; el.textContent = text; if (title) el.title = title;
    el.addEventListener('mousedown', function (event) { rememberSelection(); event.preventDefault(); });
    el.addEventListener('click', function () { try { action(); } catch (error) { message(error.message); } }); toolbar.appendChild(el); return el;
  }
  toolbar.replaceChildren();
  modeButton = button('切换为预览', function () { setEditing(!editing); });
  button('标红', function () { applyFormat('red', true); }, '只改文字颜色，保留粗体');
  button('取消标红', function () { applyFormat('red', false); }, '只取消红色，保留粗体');
  button('加粗', function () { applyFormat('bold', true); }, '只改粗体，保留颜色');
  button('取消加粗', function () { applyFormat('bold', false); }, '只取消粗体，保留颜色');
  button('删除整行', deleteWholeBlock, '删除当前正文或标题块，可用撤销恢复');
  button('添加一行', addWholeLine, '在当前光标位置添加软换行，保留现有排版样式');
  undoButton = button('撤销', function () { moveHistory(-1); });
  redoButton = button('重做', function () { moveHistory(1); });
  saveButton = button('保存草稿', saveDraft, '保存到本地 Markdown 与 HTML；有未保存修改时每 2 分钟自动保存'); saveButton.id = 'gzhSaveDraftBtn';
  status = document.createElement('span'); status.id = 'gzh-editor-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite'); toolbar.appendChild(status);
  autoSaveNotice = document.createElement('span'); autoSaveNotice.id = 'gzh-editor-autosave'; autoSaveNotice.setAttribute('aria-label', '自动保存频率'); toolbar.appendChild(autoSaveNotice);
  toolbar.setAttribute('data-editing', 'true');
  blocks.forEach(prepareBlock); commit([]); updateSaveButton(); updateAutoSaveNotice(); stateMessage();
  window.setInterval(autoSaveTick, AUTO_SAVE_INTERVAL_MS);
  if (titleInput) {
    titleInput.addEventListener('compositionstart', function () { composing = true; });
    titleInput.addEventListener('compositionend', function () { composing = false; title = titleInput.value; commit([]); });
    titleInput.addEventListener('input', function () { title = titleInput.value; if (!composing) commit([]); });
    titleInput.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && !event.altKey && /^(z|y)$/i.test(event.key)) {
        event.preventDefault(); moveHistory(event.shiftKey || event.key.toLowerCase() === 'y' ? 1 : -1);
      }
    });
  }
  content.addEventListener('click', function (event) { if (editing && event.target.closest('a')) event.preventDefault(); });
  document.addEventListener('selectionchange', rememberSelection);
  window.addEventListener('beforeunload', function (event) {
    var dirty = true;
    try { syncDOM(); dirty = stateKey() !== initialKey; } catch (error) { dirty = true; }
    if (dirty || saving || composing || unconfirmedSubmission) { event.preventDefault(); event.returnValue = ''; }
  });
  blocks.forEach(function (block) {
    var el = elements.get(block.id);
    el.addEventListener('focusin', function () { activeBlockId = block.id; });
    el.addEventListener('mousedown', function () { activeBlockId = block.id; });
    el.addEventListener('compositionstart', function () { composing = true; });
    el.addEventListener('compositionend', function () { composing = false; try { var ranges = selectionRanges(); syncDOM(); renderBlock(block); restoreSelection(ranges); commit(ranges); } catch (error) { recover(error, block); } });
    el.addEventListener('beforeinput', function (event) {
      if (!editing || composing || event.isComposing || !event.cancelable) return;
      var type = event.inputType;
      if (type === 'historyUndo' || type === 'historyRedo') { event.preventDefault(); moveHistory(type === 'historyUndo' ? -1 : 1); return; }
      if (type === 'insertText' || type === 'insertReplacementText' || type === 'insertParagraph' || type === 'insertLineBreak' || type === 'deleteContentBackward' || type === 'deleteContentForward' || type === 'deleteByCut') {
        event.preventDefault(); try { replaceSelection(type.indexOf('insert') === 0 ? (type === 'insertText' || type === 'insertReplacementText' ? event.data || '' : '\n') : '', type === 'deleteContentBackward' ? -1 : type === 'deleteContentForward' ? 1 : 0); } catch (error) { recover(error, block); } return;
      }
      // 浏览器原生格式命令、拖放和跨块结构变化不能绕过受控格式模型。
      event.preventDefault(); message('此操作不支持；请使用文字选区与上方格式按钮。');
    });
    el.addEventListener('input', function () { if (composing) return; try { var ranges = selectionRanges(); syncDOM(); renderBlock(block); restoreSelection(ranges); commit(ranges); } catch (error) { recover(error, block); } });
    el.addEventListener('paste', function (event) { event.preventDefault(); if (editing && event.clipboardData) { try { replaceSelection(event.clipboardData.getData('text/plain').replace(/\r\n?/g, '\n'), 0); } catch (error) { recover(error, block); } } });
    el.addEventListener('drop', function (event) { event.preventDefault(); message('请使用纯文字粘贴。'); });
    el.addEventListener('keydown', function (event) {
      if ((event.key === 'Backspace' || event.key === 'Delete') && selectionRanges().length > 1) {
        event.preventDefault(); try { replaceSelection('', 0); } catch (error) { message(error.message); } return;
      }
      if ((event.metaKey || event.ctrlKey) && !event.altKey && (event.key.toLowerCase() === 'z' || event.key.toLowerCase() === 'y')) { event.preventDefault(); moveHistory(event.shiftKey || event.key.toLowerCase() === 'y' ? 1 : -1); }
      if ((event.metaKey || event.ctrlKey) && /^(b|i|u)$/i.test(event.key)) { event.preventDefault(); message('请使用上方独立格式按钮。'); }
    });
    (partElements.get(block.id) || []).forEach(function (part) {
      part.addEventListener('focusin', function () { activeBlockId = block.id; });
      part.addEventListener('mousedown', function () { activeBlockId = block.id; });
      part.addEventListener('compositionstart', function () { composing = true; });
      part.addEventListener('compositionend', function () {
        composing = false;
        try { readNumberPart(block); commit([]); } catch (error) { renderNumberPart(block); message(error.message); }
      });
      part.addEventListener('beforeinput', function (event) {
        if (!editing || composing || event.isComposing || !event.cancelable) return;
        if (event.inputType === 'insertParagraph' || event.inputType === 'insertLineBreak') {
          event.preventDefault(); message('章节序号只能编辑为单行文字。');
        }
      });
      part.addEventListener('input', function () {
        if (composing) return;
        try { readNumberPart(block); commit([]); } catch (error) { renderNumberPart(block); message(error.message); }
      });
      part.addEventListener('paste', function (event) {
        event.preventDefault();
        if (!editing || !event.clipboardData) return;
        try {
          part.textContent = normalizeNumber(event.clipboardData.getData('text/plain'));
          readNumberPart(block); commit([]);
        } catch (error) { renderNumberPart(block); message(error.message); }
      });
      part.addEventListener('keydown', function (event) {
        if ((event.metaKey || event.ctrlKey) && !event.altKey && /^(z|y)$/i.test(event.key)) {
          event.preventDefault(); moveHistory(event.shiftKey || event.key.toLowerCase() === 'y' ? 1 : -1);
        }
      });
    });
  });
  window.gzhEditor = { exportPackage: exportPackage, applyFormat: applyFormat, setEditing: setEditing,
    undo: function () { return moveHistory(-1); }, redo: function () { return moveHistory(1); }, savePackage: saveDraft, saveDraft: saveDraft,
    autoSaveTick: autoSaveTick, autoSaveInterval: AUTO_SAVE_INTERVAL_MS,
    isEditing: function () { return editing; }, isDirty: function () { syncDOM(); return Boolean(unconfirmedSubmission) || stateKey() !== initialKey; } };
}());
