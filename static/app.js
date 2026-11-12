/* 提示词工作台 · 前端 v4（干净重写） */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const norm = s => String(s || '').toLowerCase().replace(/[\s_\-()（）]/g, '');
  const LS = {
    get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  };

  const CATS = ['全部', '角色', '外形', '服装', '动作', '道具', '场景', '自定义', '自定义2', '自定义3'];
  const MINE = ['自定义', '自定义2', '自定义3'];
  const CATNAME = { '自定义': '其他', '自定义2': '自定义', '自定义3': '自定义2' };
  const catLabel = () => LS.get('catLabels', {});
  const catHidden = () => LS.get('catHidden', []);
  /* 用户新建的顶级分类存在 localStorage.cats（配合 catLabels / catHidden 改名·删除） */
  const extraCats = () => (Array.isArray(LS.get('cats', [])) ? LS.get('cats', []) : [])
    .filter((c, i, a) => typeof c === 'string' && c && !CATS.includes(c) && a.indexOf(c) === i);
  const catsAll = () => CATS.concat(extraCats());
  const isMine = c => MINE.includes(c) || extraCats().includes(c);
  function labelOf(c) { return catLabel()[c] || CATNAME[c] || c; }
  const HASSUB = ['角色', '外形', '服装', '动作', '道具', '场景', '自定义'];
  const hasSub = c => HASSUB.includes(c) || extraCats().includes(c);
  /* 「角色」二级分组白名单：sub 命中这里 → 归「游戏」，否则归「动漫」。
     名字按 tags_cn.json 里 sub 字段的实际写法写（Fate / 舰Colle / 崩坏星穹铁道…）。 */
  const GAME = ['游戏', '原神', '崩坏3', '崩坏星穹铁道', '明日方舟', '蔚蓝档案', '少女前线',
    '鸣潮', '战双帕弥什', '绝区零', '公主连结', '赛马娘', '碧蓝航线', '阴阳师',
    '宝可梦', '女神异闻录5', '最终幻想7', '尼尔', '无期迷途', '重返未来1999',
    '未定事件簿', '恋与制作人', '偶像梦幻祭', 'Fate', 'Fate/stay night', '舰Colle', 'LoveLive',
    '偶像大师', '世界计划', 'BanG Dream', '胜利女神NIKKE', 'NIKKE'];
  const PAGE = 150;

  const S = { lib: [], all: [], cat: '全部', sub: '全部', q: '', nsfw: false, favTop: false,
              chars: [], global: [], shown: PAGE, sec: { moss: true, wai: true, pony: true, exp: true },
              /* 拖标签到分类芯片的改动：en → { cat, sub }。分类归属一律走 catOf()，override 优先 */
              catOverrides: {} };

  /* 分类归属：override 优先，同一个 en 只有一个分类（不叠加原分类）。
     override 允许旧的纯字符串写法（老 localStorage 数据）。 */
  const ovOf = e => (e && S.catOverrides[e.en]) || null;
  const catOf = e => {
    const o = ovOf(e);
    return (o && (typeof o === 'string' ? o : o.cat)) || (e && e.cat) || '';
  };
  const subOf = e => {
    const o = ovOf(e);
    const s = o && typeof o === 'object' ? o.sub : '';
    return s || (e && e.sub) || '';
  };

  const favs = () => new Set(LS.get('favTags', []));
  const subsCustom = c => LS.get('customSubs', {})[c] || [];
  const saveSubs = (c, a) => { const o = LS.get('customSubs', {}); o[c] = a; LS.set('customSubs', o); };
  const clamp = v => Math.max(.1, Math.min(2, +v.toFixed(1)));

  function toast(m) {
    let t = $('#toast');
    if (!t) {
      t = document.createElement('div'); t.id = 'toast';
      t.style.cssText = 'position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:999;background:linear-gradient(135deg,#5a95f7,#3a72d4);color:#fff;padding:9px 20px;border-radius:12px;font-size:13px;box-shadow:0 10px 28px rgba(76,139,245,.35);transition:opacity .25s';
      document.body.appendChild(t);
    }
    t.textContent = m; t.style.opacity = '1';
    clearTimeout(t._h); t._h = setTimeout(() => t.style.opacity = '0', 1800);
  }
  function toastSticky(msg) {
    let t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div'); t.id = 'toast';
      t.style.cssText = 'position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:999;background:linear-gradient(135deg,#5a95f7,#3a72d4);color:#fff;padding:10px 22px;border-radius:12px;font-size:13px;box-shadow:0 10px 28px rgba(76,139,245,.35)';
      document.body.appendChild(t);
    }
    t.textContent = msg; t.style.opacity = '1';
    clearTimeout(t._h);
    return () => { t.style.opacity = '0'; };
  }

  const api = (p, b) => fetch(p, { method: b === undefined ? 'GET' : 'POST', headers: { 'content-type': 'application/json' }, body: b && JSON.stringify(b) }).then(r => r.json());

  /* ===================== 通用浮层（替代原生 prompt） ===================== */
  /* 与「⚙ API 配置」同款：白底圆角卡片 + 遮罩，点遮罩 / Esc 关闭。
     fields: [{key,label,value,placeholder,type:'text'|'password'|'select',options:[{value,label}]}]
     onOk(values) 返回 false 则浮层不关（校验失败时用） */
  function openDialog(opt) {
    if (opt.id) {
      const ex = document.getElementById(opt.id);
      if (ex) { const f = ex.querySelector('input,select'); if (f) f.focus(); return; }
    }
    const fields = opt.fields || [];
    const d = document.createElement('div');
    if (opt.id) d.id = opt.id;
    d.style.cssText = 'position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:999;background:rgba(20,30,50,.35)';
    const ctl = f => {
      const st = 'width:100%;height:34px;border:1px solid #dbe6f6;border-radius:9px;padding:0 10px;font-size:13px;background:#fff';
      if (f.type === 'select') {
        return `<select data-k="${esc(f.key)}" style="${st};cursor:pointer">` +
          (f.options || []).map(o => `<option value="${esc(o.value)}"${o.value === f.value ? ' selected' : ''}>${esc(o.label)}</option>`).join('') +
          '</select>';
      }
      return `<input data-k="${esc(f.key)}"${f.type === 'password' ? ' type="password"' : ''} value="${esc(f.value == null ? '' : f.value)}"` +
        ` placeholder="${esc(f.placeholder || '')}" style="${st}">`;
    };
    d.innerHTML = `<div style="width:${opt.width || 420}px;max-height:86vh;overflow:auto;background:#fff;border-radius:16px;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.2)">
      <div style="font-weight:700;font-size:15px;margin-bottom:14px">${esc(opt.title || '')}</div>
      ${fields.map(f => `<div style="font-size:12px;color:#5a6c85">${esc(f.label)}</div>
      ${ctl(f)}
      <div style="height:10px"></div>`).join('')}
      <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:4px">
        <button class="btn" data-cancel="1">取消</button>
        <button class="btn primary" data-ok="1">${esc(opt.okText || '确定')}</button>
      </div></div>`;
    document.body.appendChild(d);
    const ctrls = [].slice.call(d.querySelectorAll('[data-k]'));
    const read = () => { const o = {}; ctrls.forEach(el => { o[el.dataset.k] = String(el.value || '').trim(); }); return o; };
    const close = () => { d.remove(); if (opt.onClose) opt.onClose(); };
    const submit = () => {
      const v = read();
      if (opt.onOk && opt.onOk(v) === false) return false;
      close(); return true;
    };
    d.querySelector('[data-cancel]').onclick = close;
    d.querySelector('[data-ok]').onclick = submit;
    d.onclick = ev => { if (ev.target === d) close(); };
    d.onkeydown = ev => {
      if (ev.key === 'Escape') close();
      else if (ev.key === 'Enter' && ev.target.tagName === 'INPUT') submit();
    };
    if (ctrls[0]) { ctrls[0].focus(); if (ctrls[0].select) ctrls[0].select(); }
    return { el: d, values: read, close, submit };
  }

  /* 单行文本输入（替代原生 prompt） */
  function askText(title, label, value, onOk) {
    return openDialog({
      title, fields: [{ key: 'v', label, value: value || '' }],
      onOk: v => onOk(String(v.v || '').trim()),
    });
  }

  /* ===================== 分类 ===================== */
  function renderCats() {
    $('#catGrid').innerHTML = catsAll().filter(c => !catHidden().includes(c)).map(c =>
      `<span class="chip ${S.cat === c ? 'on' : ''}" data-cat="${esc(c)}" data-mine="${isMine(c) ? 1 : 0}">${esc(labelOf(c))}${hasSub(c) ? ' ▾' : ''}</span>`).join('');
    $('#catGrid').querySelectorAll('.chip').forEach(el => {
      el.onclick = () => { S.cat = el.dataset.cat; S.sub = '全部'; S.shown = PAGE; renderCats(); renderSub(); renderTags(); };
      if (el.dataset.mine === '1') {
        el.oncontextmenu = ev => {
          ev.preventDefault();
          const c = el.dataset.cat;
          askText('重命名分类', '输入新名字；留空则删除该分类', labelOf(c), ans => {
            if (!ans) {
              const hid = catHidden(); if (!hid.includes(c)) hid.push(c); LS.set('catHidden', hid);
              if (S.cat === c) S.cat = '全部';
    // 恢复上次的已选（刷新不清空）
    try {
      const st = LS.get('selState', null);
      if (st && typeof st === 'object') {
        if (Array.isArray(st.chars)) S.chars = st.chars;
        if (Array.isArray(st.global)) S.global = st.global;
      }
    } catch (_) {}
    renderCats(); renderSub(); renderTags(); renderSel();
              toast('已删除分类：' + labelOf(c));
              return;
            }
            if (ans === labelOf(c)) return;
            const o = catLabel(); o[c] = ans; LS.set('catLabels', o);
            renderCats(); renderSub(); renderTags();
            toast('已改名：' + ans);
          });
        };
      }
      el.ondragover = e => { if (hasSub(el.dataset.cat)) { e.preventDefault(); el.style.borderColor = '#5a95f7'; } };
      el.ondragleave = () => el.style.borderColor = '';
      el.ondrop = e => {
        e.preventDefault(); el.style.borderColor = '';
        const en = e.dataTransfer.getData('text/plain');
        if (en && hasSub(el.dataset.cat)) moveTag(en, el.dataset.cat, '');
      };
    });

    $('#catAct').innerHTML = `
      <span class="act fav"><label class="sw"><input type="checkbox" id="cbFav" ${S.favTop ? 'checked' : ''}>★ 收藏</label></span>
      <span class="act" id="actArt">🎨 画风库</span>
      <span class="act nsfw"><label class="sw"><input type="checkbox" id="cbNsfw" ${S.nsfw ? 'checked' : ''}>🔞 NSFW</label></span>
      <span class="act" id="actTrash">🗑 垃圾桶</span>`;
    $('#cbFav').onchange = e => { S.favTop = e.target.checked; saveSettings(); renderTags(); };
    $('#cbNsfw').onchange = e => { S.nsfw = e.target.checked; saveSettings(); renderTags(); };
    $('#actArt').onclick = openStyles;
    const tr = $('#actTrash');
    tr.ondragover = e => { e.preventDefault(); tr.classList.add('hot'); };
    tr.ondragleave = () => tr.classList.remove('hot');
    tr.ondrop = e => {
      e.preventDefault(); tr.classList.remove('hot');
      if (delDrag()) { toast('已删除'); return; }
      const dc = window.__dragChar;
      if (dc) {
        window.__dragChar = null;
        delCustomChar(dc.en, dc.zh);
        return;
      }
      if (window.__dragSub) {
        const { cat, name } = window.__dragSub;
        const arr = subsCustom(cat).filter(x => x !== name);
        saveSubs(cat, arr);
        if (S.sub === name) S.sub = '全部';
        window.__dragSub = null;
        renderSub(); renderTags();
        toast('已删除分类：' + name);
        return;
      }
      toast('把标签或自定义分类拖到这里删除');
    };
  }

  function subsOf(cat) {
    if (cat === '角色') {
      const base = ['游戏', '动漫', 'MOSS原创'];
      if (S.lib.some(e => catOf(e) === '角色' && e.custom)) base.push('自定义');
      return base;
    }
    if (cat === '道具') return ['日常', 'NSFW'];
    const m = new Map();
    S.lib.filter(e => catOf(e) === cat).forEach(e => { const k = subOf(e) || '全部'; m.set(k, (m.get(k) || 0) + 1); });
    return [...m.entries()].sort((a, b) => b[1] - a[1]).map(x => x[0]);
  }

  function renderSub() {
    const box = $('#submenu');
    if (!hasSub(S.cat)) { box.style.display = 'none'; return; }
    box.style.display = 'flex';
    $('#subTitle').textContent = labelOf(S.cat);
    const list = $('#subList');
    const base = ['全部'].concat(subsOf(S.cat));
    list.innerHTML = base.map(s => `<span class="${S.sub === s ? 'on' : ''}" data-sub="${esc(s)}">${esc(s)}</span>`).join('') +
      subsCustom(S.cat).map(s => `<span class="${S.sub === s ? 'on' : ''} cust" data-sub="${esc(s)}" title="双击改名">${esc(s)}<b style="margin-left:4px;color:#c8d3e2;cursor:pointer" data-del-sub="${esc(s)}">×</b></span>`).join('') +
      `<span class="addchar" id="addSub">＋ 新增分类</span>` +
      (S.cat === '角色' ? '<span class="addchar" id="addChar">＋ 添加角色</span>' : '');

    list.querySelectorAll('[data-sub]').forEach(el => {
      el.onclick = () => { S.sub = el.dataset.sub; S.shown = PAGE; renderSub(); renderTags(); };
      el.ondragover = e => { e.preventDefault(); el.style.borderColor = '#5a95f7'; };
      el.ondragleave = () => el.style.borderColor = '';
      el.ondrop = e => {
        e.preventDefault(); el.style.borderColor = '';
        const en = e.dataTransfer.getData('text/plain');
        if (!en) return;
        if (el.dataset.sub === '全部') { toast('拖到具体子分类'); return; }
        moveTag(en, S.cat, el.dataset.sub);
      };
      if (el.classList.contains('cust')) {
        el.ondblclick = ev => {
          ev.stopPropagation();
          const name = el.dataset.sub;
          askText('重命名子分类', '输入新名字', name, ans => {
            if (!ans || ans === name) return;
            const arr = subsCustom(S.cat); const i = arr.indexOf(name);
            if (i >= 0) arr[i] = ans;
            if (S.sub === name) S.sub = ans;
            saveSubs(S.cat, arr); renderSub(); renderTags();
            toast('已改名：' + ans);
          });
        };
        el.draggable = true;
        el.ondragstart = ev => {
          window.__dragSub = { cat: S.cat, name: el.dataset.sub };
          window.__dragChar = null; window.__dragSel = null;
          ev.dataTransfer.setData('text/plain', 'sub');
        };
        el.oncontextmenu = ev => {
          ev.preventDefault();
          const name = el.dataset.sub;
          askText('重命名子分类', '输入新名字；留空则删除该子分类', name, ans => {
            const arr = subsCustom(S.cat); const i = arr.indexOf(name);
            if (!ans) { if (i >= 0) arr.splice(i, 1); if (S.sub === name) S.sub = '全部'; }
            else if (i >= 0) { arr[i] = ans; if (S.sub === name) S.sub = ans; }
            saveSubs(S.cat, arr); renderSub(); renderTags();
            toast(ans ? '已改名：' + ans : '已删除子分类：' + name);
          });
        };
      }
    });
    list.querySelectorAll('[data-del-sub]').forEach(b => b.onclick = ev => {
      ev.stopPropagation();
      const name = b.dataset.delSub;
      const arr = subsCustom(S.cat).filter(x => x !== name);
      saveSubs(S.cat, arr);
      if (S.sub === name) S.sub = '全部';
      renderSub(); renderTags();
      toast('已删除分类：' + name);
    });
    $('#addSub').onclick = () => {
      const cat = S.cat;
      openDialog({
        title: '＋ 新增分类',
        fields: [
          { key: 'name', label: '分类名称', placeholder: '例如：JK / 泳装 / 原创角色' },
          { key: 'scope', label: '加到哪里', type: 'select', value: 'top', options: [
            { value: 'top', label: '顶级分类（左栏分类芯片，可改名 / 删除）' },
            { value: 'sub', label: '当前分类「' + labelOf(cat) + '」下的子分类' },
          ] },
        ],
        onOk: v => {
          const n = String(v.name || '').trim();
          if (!n) { toast('请填写分类名称'); return false; }
          if (v.scope === 'sub') {
            const a = subsCustom(cat);
            if (a.includes(n)) { toast('子分类已存在'); return false; }
            a.push(n); saveSubs(cat, a);
            S.sub = n;
          } else {
            if (catsAll().includes(n)) { toast('分类已存在'); return false; }
            const a = extraCats().concat(n); LS.set('cats', a);
            const hid = catHidden().filter(x => x !== n); LS.set('catHidden', hid);
            S.cat = n; S.sub = '全部';
          }
          S.shown = PAGE;
          renderCats(); renderSub(); renderTags();
          toast('已新增分类：' + n);
        },
      });
    };
    const ac = $('#addChar'); if (ac) ac.onclick = addCharacter;
  }

  /* 拖到分类芯片 / 子分类芯片：写 override，不改词库。
     override 按 en 生效 → 该 en 的所有重复条目一起搬家，原分类里不再残留。
     拖回「原分类 + 原子分类」时删掉 override，回到词库默认归属。 */
  function moveTag(en, cat, sub) {
    const hits = S.lib.filter(x => x.en === en);
    if (!hits.length) return;
    const base = hits[0];
    const cur = ovOf(base);
    const curSub = (cur && typeof cur === 'object' ? cur.sub : '') || base.sub || '';
    const nextSub = sub || curSub;
    if (base.cat === cat && (base.sub || '') === (nextSub || '')) delete S.catOverrides[en];
    else S.catOverrides[en] = { cat: cat, sub: nextSub };
    LS.set('catOverrides', S.catOverrides);
    toast('已移到 ' + labelOf(cat) + (sub ? ' / ' + sub : ''));
    renderSub(); renderTags();
  }

  /* ===================== 标签列表 ===================== */
  function computeList() {
    const q = norm(S.q);
    /* 同一 en 可能在词库里出现多条（跨分类重复）：按词库顺序只认第一条为「代表」，
       归类看 catOf(代表)，所以一个 en 永远只出现在一个分类里。
       搜索仍匹配该 en 的全部中文别名（发绳 / 头绳 都能搜到）。 */
    const alias = new Map();
    S.lib.forEach(e => {
      const k = e.en || e.zh;
      alias.set(k, (alias.get(k) || '') + '|' + norm(e.zh) + '|' + norm(e.sub));
    });
    const seen = new Set();
    const list = [];
    for (const e of S.lib) {
      const key = e.en || e.zh;
      if (seen.has(key)) continue;
      seen.add(key);
      if (!S.nsfw && e.nsfw) continue;
      const cat = catOf(e);
      if (S.cat !== '全部' && cat !== S.cat) continue;
      if (S.cat === '道具') {
        if (S.sub === '日常' && e.nsfw) continue;
        if (S.sub === 'NSFW' && !e.nsfw) continue;
      } else if (S.cat === '角色') {
        const sb = subOf(e);
        if (S.sub === '游戏' && !GAME.includes(sb)) continue;
        if (S.sub === '动漫' && (GAME.includes(sb) || e.custom)) continue;
        if (S.sub === 'MOSS原创' && sb !== 'MOSS原创') continue;
        if (S.sub === '自定义' && !e.custom) continue;
      } else if (S.sub !== '全部' && !subsCustom(S.cat).includes(S.sub)) {
        if ((subOf(e) || '全部') !== S.sub) continue;
      }
      /* 关键词同时匹配中文名 / 英文 tag / 作品名(sub)，命中作品名即列出该作品全部角色 */
      if (q && !(norm(e.zh).includes(q) || norm(e.en).includes(q) || norm(subOf(e)).includes(q) || (alias.get(key) || '').includes(q))) continue;
      list.push(e);
    }
    const f = favs();
    if (S.favTop) list.sort((a, b) => (f.has(b.en) ? 1 : 0) - (f.has(a.en) ? 1 : 0));
    if (S.nsfw) list.sort((a, b) => (b.nsfw ? 1 : 0) - (a.nsfw ? 1 : 0));
    /* 「角色」分类（含 游戏 / 动漫 / 自定义 等子分类芯片）：内置精修 + 用户自定义排在前面，
       sub == "图反推" 的角色一律排到最后。只切两段、不重排段内顺序（词库顺序 / 收藏置顶 /
       NSFW 置顶的相对次序都保留），其它分类完全不受影响。 */
    if (S.cat === '角色') {
      const main = [], reverse = [];
      list.forEach(e => (subOf(e) === '图反推' ? reverse : main).push(e));
      return main.concat(reverse);
    }
    return list;
  }

  function renderTags() {
    const box = $('#tagList');
    const list = computeList();
    S.all = list;
    const total = new Set(S.lib.map(e => e.en || e.zh)).size;
    $('#libCount').textContent = list.length + ' / ' + total + ' · 热度';
    const f = favs();
    box.innerHTML = list.slice(0, S.shown).map(e => `
      <div class="tag" draggable="true" data-en="${esc(e.en)}">
        <span class="favbtn ${f.has(e.en) ? 'on' : ''}" data-fav="${esc(e.en)}">★</span>
        <span class="zht">${esc(e.zh)}</span><i>${esc(e.en)}</i>
      </div>`).join('') || '<div class="empty">没有匹配的标签</div>';
    box.querySelectorAll('.tag').forEach(el => {
      el.onclick = ev => { if (ev.target.classList.contains('favbtn')) return; addTag(el.dataset.en); };
      el.oncontextmenu = ev => {
        const c = S.lib.find(x => x.en === el.dataset.en);
        if (!c || catOf(c) !== '角色') return;
        ev.preventDefault();
        editCharacter(c);
      };
      el.ondragstart = ev => {
        const c = S.lib.find(x => x.en === el.dataset.en);
        window.__dragChar = c ? customCharOf(c.en, c.zh) : null;
        window.__dragSub = null; window.__dragSel = null;
        ev.dataTransfer.setData('text/plain', el.dataset.en);
      };
    });
    box.querySelectorAll('.favbtn').forEach(el => el.onclick = ev => {
      ev.stopPropagation();
      const s = favs(); s.has(el.dataset.fav) ? s.delete(el.dataset.fav) : s.add(el.dataset.fav);
      LS.set('favTags', [...s]); renderTags();
    });
  }

  function initScroll() {
    const box = $('#tagList');
    box.addEventListener('scroll', () => {
      if (box.scrollTop + box.clientHeight < box.scrollHeight - 60) return;
      if (S.shown >= S.all.length) return;
      S.shown += PAGE; renderTags();
    });
  }

  /* ===================== 已选 ===================== */
  function addTag(en) {
    const t = S.lib.find(x => x.en === en); if (!t) return;
    if (!S.nsfw && t.nsfw) { toast('NSFW 标签，先开开关'); return; }
    if (catOf(t) === '角色') {
      if (S.chars.some(c => c.name === t.zh)) { toast('已在角色框里'); return; }
      S.chars.push({ name: t.zh, app: t.app || null, tags: [] });
      renderSel(); toast('已建立角色框：' + t.zh); return;
    }
    if (S.global.some(x => x.en === en)) { toast('已在已选里'); return; }
    S.global.push({ zh: t.zh, en: t.en, w: 1 });
    renderSel();
  }

  function delDrag() {
    const p = window.__dragSel;
    if (!p) return false;
    if (p.from === 'g') S.global.splice(p.j, 1);
    else S.chars[p.i].tags.splice(p.j, 1);
    window.__dragSel = null; renderSel(); return true;
  }


  const PAIR_CONFLICT = [
    [['裸体', '全裸', '裸体围裙'], ['校服', '连衣裙', '衬衫', '制服', '女仆', '和服', '泳装', '比基尼']],
    [['室内', '卧室', '教室', '客厅'], ['室外', '街道', '公园', '海滩']],
    [['一个人', '1girl'], ['两个', '2girls', '多人']],
    [['笑'], ['哭']],
  ];
  function detectConflicts() {
    const all = S.global.map(t => t.zh)
      .concat(...S.chars.map(c => c.tags.map(t => t.zh)));
    const out = [];
    PAIR_CONFLICT.forEach(([A, B]) => {
      const a = all.find(z => A.some(k => z.includes(k)));
      const b = all.find(z => B.some(k => z.includes(k)) && z !== a);
      if (a && b) out.push(a + ' × ' + b);
    });
    if (S.chars.length >= 2) {
      const dup = new Set();
      S.chars.forEach(c => { if (c.name) { if (dup.has(c.name)) out.push('重复角色：' + c.name); dup.add(c.name); } });
    }
    return out;
  }

  function saveSel() {
    try {
      LS.set('selState', { chars: S.chars, global: S.global });
    } catch (_) {}
  }
  function renderSel() {
    saveSel();
    const body = $('#selBody');
    $('#selCount').textContent = S.global.length + S.chars.reduce((n, c) => n + c.tags.length, 0);
    const cf = detectConflicts();
    const okHtml = cf.length
      ? `<div class="ok" style="background:#fff5f5;border-color:#ffd9d9;color:#d45050">⚠ 冲突：${cf.join('；')}</div>`
      : '<div class="ok">✓ 无冲突</div>';
    body.innerHTML = okHtml +
      S.chars.map((c, i) => `<div class="box" data-char="${i}">
        <div class="n">${esc(c.name)}<span class="x" data-delchar="${i}">×</span></div>
        <div class="tlist">${c.tags.map((t, j) =>
          `<span class="t" draggable="true" data-tag="${i},${j}">${esc(t.zh)}
            <span class="w"><span data-w="${i},${j},-1">−</span><b>${t.w.toFixed(1)}</b><span data-w="${i},${j},1">+</span></span></span>`).join('')
          || '<span class="hintdrop">把标签拖进来 = 归给她</span>'}</div></div>`).join('') +
      `<div class="gsec"><div class="gn">全局标签<span class="x" data-clear="1">×</span></div>
        <div class="tgrid" data-gdrop="1">${S.global.map((t, j) =>
          `<div class="tcard" draggable="true" data-gtag="${j}">
            <span class="x" data-gdel="${j}">×</span><span class="s">★</span><span class="zh">${esc(t.zh)}</span>
            <span class="en">${esc(t.en)}</span>
            <div class="row"><span data-gw="${j},-1">−</span><b>${t.w.toFixed(1)}</b><span data-gw="${j},1">+</span></div></div>`).join('')
          || '<span class="hintdrop">点左侧标签加入，或把标签拖到这</span>'}</div></div>`;

    body.querySelectorAll('[data-gw]').forEach(el => el.onclick = () => {
      const [j, d] = el.dataset.gw.split(',').map(Number);
      const t = S.global[j]; t.w = clamp(t.w + d * .1); renderSel();
    });
    body.querySelectorAll('[data-w]').forEach(el => el.onclick = () => {
      const [i, j, d] = el.dataset.w.split(',').map(Number);
      const t = S.chars[i].tags[j]; t.w = clamp(t.w + d * .1); renderSel();
    });
    body.querySelectorAll('[data-gtag]').forEach(card => {
      const j = +card.dataset.gtag, t = S.global[j];
      if (!t) return;
      const star = card.querySelector('.s');
      if (!star) return;
      const f = favs();
      star.textContent = f.has(t.en) ? '★' : '☆';
      star.style.cursor = 'pointer';
      star.onclick = ev => {
        ev.stopPropagation();
        const s2 = favs();
        s2.has(t.en) ? s2.delete(t.en) : s2.add(t.en);
        LS.set('favTags', [...s2]);
        renderSel(); renderTags();
        toast(s2.has(t.en) ? '已收藏' : '已取消收藏');
      };
    });
    body.querySelectorAll('[data-gdel]').forEach(el => el.onclick = () => { S.global.splice(+el.dataset.gdel, 1); renderSel(); });
    body.querySelectorAll('[data-delchar]').forEach(el => el.onclick = () => { S.chars.splice(+el.dataset.delchar, 1); renderSel(); });
    const clr = body.querySelector('[data-clear]'); if (clr) clr.onclick = () => { S.global = []; renderSel(); };

    body.querySelectorAll('[draggable="true"]').forEach(el => {
      el.ondragstart = ev => {
        window.__dragChar = null; window.__dragSub = null;
        window.__dragSel = el.dataset.tag
          ? { from: 'c', i: +el.dataset.tag.split(',')[0], j: +el.dataset.tag.split(',')[1] }
          : { from: 'g', j: +el.dataset.gtag };
        ev.dataTransfer.setData('text/plain', 'sel');
      };
    });
    body.querySelectorAll('[data-char]').forEach(box => {
      box.ondragover = e => e.preventDefault();
      box.ondrop = e => {
        e.preventDefault();
        const idx = +box.dataset.char, p = window.__dragSel;
        if (p) {
          if (p.from === 'g') { const t = S.global[p.j]; if (t) S.chars[idx].tags.push({ zh: t.zh, en: t.en, w: t.w }); S.global.splice(p.j, 1); }
          else if (p.i !== idx) { const t = S.chars[p.i].tags[p.j]; S.chars[idx].tags.push(t); S.chars[p.i].tags.splice(p.j, 1); }
          window.__dragSel = null; renderSel(); return;
        }
        const en = e.dataTransfer.getData('text/plain');
        if (en) { const t = S.lib.find(x => x.en === en); if (t) { S.chars[idx].tags.push({ zh: t.zh, en, w: 1 }); renderSel(); } }
      };
    });
    const gd = body.querySelector('[data-gdrop]');
    gd.ondragover = e => e.preventDefault();
    gd.ondrop = e => {
      e.preventDefault();
      const p = window.__dragSel;
      if (p && p.from === 'c') {
        const t = S.chars[p.i].tags[p.j];
        if (t) S.global.push({ zh: t.zh, en: t.en, w: t.w });
        S.chars[p.i].tags.splice(p.j, 1); window.__dragSel = null; renderSel(); return;
      }
      const en = e.dataTransfer.getData('text/plain');
      if (en) addTag(en);
    };
  }

  /* ===================== 结果 ===================== */
  function renderChips() {
    const map = [['moss', 'MOSS'], ['wai', 'WAI'], ['pony', 'Pony'], ['anima', 'Animagine'], ['krea', 'Krea2'], ['exp', '扩写结果']];
    $('#secChips').innerHTML = map.map(([k, n]) =>
      `<span class="swchip ${S.sec[k] ? 'on' : ''}" data-k="${k}">${n}</span>`).join('');
    $('#secChips').querySelectorAll('.swchip').forEach(el => el.onclick = () => {
      S.sec[el.dataset.k] = !S.sec[el.dataset.k];
      el.classList.toggle('on', S.sec[el.dataset.k]);
      applySec();
    });
  }
  function applySec() {
    document.querySelectorAll('#resBody .sec').forEach(el => {
      el.style.display = S.sec[el.dataset.sec] ? '' : 'none';
    });
  }
  function showResult(rows) {
    const body = $('#resBody');
    body.innerHTML = rows.map(([k, v]) => {
      const sec = /MOSS/.test(k) ? 'moss' : /WAI/.test(k) ? 'wai' : /Pony/.test(k) ? 'pony' : /Animagine/.test(k) ? 'anima' : /Krea/.test(k) ? 'krea' : 'exp';
      const fill = sec === 'exp' ? '<u data-fill="1">填入草稿</u>' : '';
      return `<div class="sec" data-sec="${sec}">
        <div class="lbl">${esc(k)}<span class="r">${fill}<u data-copy="${esc(k)}">复制</u></span></div>
        <div class="out" data-k="${esc(k)}">${esc(v)}</div></div>`;
    }).join('');
    applySec();
    body.querySelectorAll('u[data-copy]').forEach(el => el.onclick = () => {
      const b = body.querySelector('.out[data-k="' + el.dataset.copy + '"]');
      navigator.clipboard.writeText(b ? b.textContent : ''); toast('已复制');
    });
    body.querySelectorAll('[data-fill]').forEach(el => el.onclick = () => {
      const exp = body.querySelector('.out[data-k="扩写结果"]');
      if (exp) { $('#draft').value = exp.textContent; toast('已填入草稿'); }
    });
  }

  /* ===================== 外貌 ===================== */
  const RE = {
    hair: /(黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿)发|长发|短发|双马尾|马尾|丸子头|麻花辫|卷发|直发|刘海/,
    eyes: /(黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿)(色)?(的)?(眼|瞳)/,
    outfit: /裸|全裸|没穿|不穿|内衣|围裙|校服|水手服|女仆|巫女|浴衣|和服|旗袍|泳装|比基尼|制服|连衣裙|衬衫|T恤|外套|睡衣|运动服|裙子|短裤/,
    body: /娇小|纤细|高挑|丰满|匀称/,
    chest: /贫乳|巨乳|爆乳|平胸|小胸|大胸/,
  };
  const APP_KEYS = ['hair', 'eyes', 'outfit', 'body', 'chest'];
  const randApp = {};
  const appOf = n => { const e = S.lib.find(x => x.cat === '角色' && x.zh === n); return e && e.app ? e.app : null; };
  function fillApp(name, desc) {
    let app = appOf(name);
    if (!app) {
      if (!randApp[name]) randApp[name] = { hair: '黑色长发', eyes: '蓝色眼睛', outfit: '白色连衣裙', body: '标准', chest: '标准' };
      app = randApp[name];
    }
    const parts = ['hair', 'eyes', 'outfit', 'body', 'chest'].filter(k => !RE[k].test(desc) && app[k]).map(k => app[k]);
    return parts.length ? parts.join('，') + '，' + desc : desc;
  }
  /* 英文 key：小写 + 下划线；留空则用中文名当 key */
  function charKey(zh, en) {
    const s = String(en || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    return s || String(zh || '').trim();
  }
  /* 把 localStorage.customChars 合并进标签库（按 en / 中文名去重；服务端已带回的不重复加） */
  function mergeCustomChars(list, prefer) {
    const arr = Array.isArray(list) ? list : (LS.get('customChars', []) || []);
    arr.forEach(c => {
      if (!c || !c.zh) return;
      const en = c.en || charKey(c.zh, '');
      const app = c.app || {};
      const hit = S.lib.find(e => e.en === en) || S.lib.find(e => e.cat === '角色' && e.zh === c.zh);
      if (hit) {
        if (!hit.app) hit.app = app;
        if (c.sub) hit.sub = c.sub;                                  // 作品随编辑同步进 S.lib
        if (prefer) {
          const ha = hit.app || {};
          APP_KEYS.forEach(k => { if (app[k]) ha[k] = app[k]; });   // 只覆盖填了的字段
          hit.app = ha;
        }
        return;
      }
      S.lib.push({ zh: c.zh, en, cat: '角色', sub: c.sub || '自定义', nsfw: false, app, custom: true });
    });
  }
  function addCharacter() {
    openDialog({
      title: '＋ 添加角色',
      width: 460,
      fields: [
        { key: 'zh', label: '中文名（必填）', placeholder: '例如：初音未来' },
        { key: 'en', label: '英文 tag', placeholder: '自动转小写下划线；留空用中文名当 key' },
        { key: 'sub', label: '作品', placeholder: '例如：龙与虎 / 明日方舟；留空归「自定义」' },
        { key: 'hair', label: '发色 / 发型', placeholder: '例如：蓝色长双马尾' },
        { key: 'eyes', label: '眼睛', placeholder: '例如：青色眼睛' },
        { key: 'outfit', label: '服装', placeholder: '例如：白色连衣裙' },
        { key: 'body', label: '体型', placeholder: '例如：娇小 / 纤细 / 高挑 / 丰满' },
        { key: 'chest', label: '胸围', placeholder: '例如：贫乳 / 标准 / 巨乳' },
      ],
      okText: '添加',
      onOk: v => {
        const zh = String(v.zh || '').trim();
        if (!zh) { toast('请填写中文名'); return false; }
        const en = charKey(zh, v.en);
        const sub = String(v.sub || '').trim() || '自定义';
        const app = { hair: v.hair || '', eyes: v.eyes || '', outfit: v.outfit || '',
                      body: v.body || '', chest: v.chest || '' };
        const existed = S.lib.some(e => e.en === en || (e.cat === '角色' && e.zh === zh));
        const arr = (LS.get('customChars', []) || []).filter(c => c && c.zh !== zh && c.en !== en);
        arr.push({ zh, en, sub, app });
        LS.set('customChars', arr);
        mergeCustomChars(arr, true);
        api('/api/chars', { zh, en, sub, app }).catch(() => {});
        S.cat = '角色'; S.sub = '自定义'; S.shown = PAGE;
        renderCats(); renderSub(); renderTags();
        toast((existed ? '已更新角色：' : '已添加角色：') + zh + '（点它即可加入角色框）');
      },
    });
  }

  /* 右键角色标签卡 → 编辑角色。
     自定义角色：更新 customChars 里同一条；内置角色：不改词库，写一条覆盖记录
     （带 from=原 en，后端 load_lib 按它替换内置条目；前端 mergeCustomChars 也会并 app）。 */
  function editCharacter(entry) {
    if (!entry || catOf(entry) !== '角色') return;
    const app = entry.app || {};
    const oldZh = entry.zh || '';
    const oldEn = entry.en || '';
    const oldSub = entry.sub || '';
    const inCustom = (LS.get('customChars', []) || []).some(c => c && (
      (c.en && c.en === oldEn) || (c.zh && c.zh === oldZh) || (c.from && c.from === oldEn)));
    const builtin = !(entry.custom === true || inCustom);
    const fromEn = entry.from || (builtin ? oldEn : '');
    openDialog({
      id: 'dlgEditChar',
      title: '编辑角色：' + oldZh,
      width: 460,
      fields: [
        { key: 'zh', label: '中文名（必填）', value: oldZh },
        { key: 'en', label: '英文 tag', value: oldEn, placeholder: '自动转小写下划线；留空用中文名当 key' },
        { key: 'sub', label: '作品', value: oldSub, placeholder: '例如：龙与虎 / 明日方舟；留空不改' },
        { key: 'hair', label: '发色 / 发型', value: app.hair || '', placeholder: '例如：蓝色长双马尾' },
        { key: 'eyes', label: '眼睛', value: app.eyes || '', placeholder: '例如：青色眼睛' },
        { key: 'outfit', label: '服装', value: app.outfit || '', placeholder: '例如：白色连衣裙' },
        { key: 'body', label: '体型', value: app.body || '', placeholder: '例如：娇小 / 纤细 / 高挑 / 丰满' },
        { key: 'chest', label: '胸围', value: app.chest || '', placeholder: '例如：贫乳 / 标准 / 巨乳' },
      ],
      okText: '保存',
      onOk: v => {
        const zh = String(v.zh || '').trim();
        if (!zh) { toast('请填写中文名'); return false; }
        const en = charKey(zh, v.en);
        const sub = String(v.sub || '').trim() || oldSub;
        const nextApp = { hair: v.hair || '', eyes: v.eyes || '', outfit: v.outfit || '',
                          body: v.body || '', chest: v.chest || '' };
        const keep = (LS.get('customChars', []) || []).filter(c => !(c && (
          (c.en && (c.en === oldEn || c.en === en)) ||
          (c.zh && (c.zh === oldZh || c.zh === zh)) ||
          (c.from && (c.from === fromEn || c.from === oldEn)))));
        const rec = { zh, en, app: nextApp };
        if (sub) rec.sub = sub;
        if (fromEn) rec.from = fromEn;
        keep.push(rec);
        LS.set('customChars', keep);
        api('/api/chars', rec).catch(() => {});
        entry.zh = zh; entry.en = en; entry.app = nextApp; entry.custom = true;
        if (sub) entry.sub = sub;
        if (fromEn) entry.from = fromEn;
        S.global.forEach(t => { if (t.en === oldEn) { t.en = en; t.zh = zh; } });
        S.chars.forEach(c => { if (c.name === oldZh) { c.name = zh; c.app = nextApp; } });
        renderCats(); renderSub(); renderTags(); renderSel();
        toast('已更新角色：' + zh);
      },
    });
  }

  /* 拖的是不是自定义角色：标签库里 custom 标记，或 localStorage.customChars 里有同 en / 中文名 */
  function customCharOf(en, zh) {
    const hit = S.lib.find(e => e && e.custom === true && ((en && e.en === en) || (zh && e.zh === zh)));
    if (hit) return { en: hit.en || en, zh: hit.zh || zh };
    const c = (LS.get('customChars', []) || []).find(c => c && ((en && c.en === en) || (zh && c.zh === zh)));
    return c ? { en: c.en || en, zh: c.zh || zh } : null;
  }

  /* 删除自定义角色：后端 custom_chars.json → localStorage.customChars → S.lib → 已选角色框 */
  async function delCustomChar(en, zh) {
    const rec = customCharOf(en, zh);
    const name = (rec && rec.zh) || zh || en || '';
    try {
      await fetch('/api/chars?en=' + encodeURIComponent(en || '')
        + (zh ? '&zh=' + encodeURIComponent(zh) : ''), { method: 'DELETE' });
    } catch (e) {}
    const arr = (LS.get('customChars', []) || []).filter(c => c && !((en && c.en === en) || (zh && c.zh === zh)));
    LS.set('customChars', arr);
    S.lib = S.lib.filter(e => !(e && e.custom === true && ((en && e.en === en) || (zh && e.zh === zh))));
    S.chars = S.chars.filter(c => !(c && ((zh && c.name === zh) || (en && c.name === en))));
    if (S.sub === '自定义' && !S.lib.some(e => e.cat === '角色' && e.custom)) S.sub = '全部';
    renderCats(); renderSub(); renderTags(); renderSel();
    toast('已删除角色：' + name);
  }

  /* ===================== 动作 ===================== */
  const draftText = () => ($('#draft').value || '').trim();

  async function doParse() {
    let text = draftText();
    if (!text) text = ($('#nl').value || '').trim();
    if (text.length < 4) { toast('先写一段描述或草稿'); return; }
    toast('拆解中…');
    try {
      const d = await api('/api/parse', { text });
      if (d.error) throw new Error(d.error);
      (d.chars || []).forEach(c => {
        const nm = c.zh || c.tag || '';
        const desc = c.desc || text.split(/[。\n]/).filter(x => x.includes(nm)).join('，');
        const zhs = c.features || [];
        const ens = c.features_en || [];
        const tags = zhs.map((z, i) => ({ zh: z, en: ens[i] || z, w: 1 }));
        const old = S.chars.find(x => x.name === nm);
        if (old) {
          // 同一个角色：保留角色框里已有的标签，只补新的
          tags.forEach(t => { if (!old.tags.some(o => o.en === t.en)) old.tags.push(t); });
          if (desc && desc.length > (old.desc || '').length) old.desc = desc;
        } else {
          S.chars.push({ name: nm, desc, tags });
        }
      });
      (d.tags || []).forEach(t => {
        const x = S.lib.find(e => e.en === t.en || e.en === t.tag);
        const zh = (x && x.zh) || t.zh || '';
        if (!zh) return;
        if (!S.global.some(g => g.en === (t.en || t.tag))) S.global.push({ zh, en: t.en || t.tag, w: 1 });
      });
      renderSel();
      toast('拆出 ' + (S.chars.length || S.global.length) + ' 个');
    } catch (e) { toast('拆解失败：' + e.message); }
  }

  async function doExpand() {
    const text = ($('#nl').value || '').trim();
    if (!text) { toast('先写描述'); return; }
    toast('扩写中…');
    try {
      const d = await api('/api/expand', { text, apiFull: $('#swApi').checked, nsfw: $('#swNsfwTop') ? $('#swNsfwTop').checked : false });
      const ex = (d.expanded || '').trim();
      if (!ex) { toast('扩写无内容'); return; }
      showResult([['扩写结果', ex]]);
      saveHist(ex);
      const nf = Number(d.filtered) || 0;
      toast('扩写完成' + (nf > 0 ? '（已过滤 ' + nf + ' 处露骨内容）'
                                : (d.engine ? '（' + d.engine + '）' : '')));
    } catch (e) { toast('扩写失败：' + e.message); }
  }

  function buildChars() {
    return S.chars.map(c => ({
      name: c.name, zh: c.name, en: c.en || '', pos: '',
      app: c.app || null,          // 编辑过的外观（发色/瞳色/服装）随请求带上，后端缺 app 时才回退
      desc: c.desc ? fillApp(c.name, c.desc) : '',
      tags: c.tags.map(function (t) {
        var en = t.en || t.tag;
        if (!en && t.zh) { var hit = S.lib.find(function (e) { return e.zh === t.zh; }); if (hit) en = hit.en; }
        return { tag: en || t.zh, weight: t.w || 1 };
      }),
    }));
  }
  async function doGenerate() {
    if (!S.global.length && !S.chars.length) { toast('先选标签'); return; }
    const tags = S.global.map(t => ({ tag: t.en, weight: t.w }));
    const stopWait = toastSticky('生成中…（含本地润色，预计 40-90 秒）');
    try {
      const wantMoss = S.sec.moss !== false;
      const d = await api('/api/generate', {
        tags: tags, chars: buildChars(),
        ai: false, density: $('#selDensity').value, nsfw: (function(){var e=document.getElementById('swNsfwTop');return e?!!e.checked:false;})(), mossPolish: wantMoss,
        polishMode: $('#selPolish') ? $('#selPolish').value : 'api',
        apiFull: document.getElementById('swApi').checked,
        neg: $('#selNeg') ? $('#selNeg').value : 'full',
        use: { wai: 1, pony: 1, moss: wantMoss ? 1 : 0 }, only: 'fast',
      });
      showResult(wantMoss ? [
        ['MOSS 中文', d.moss || '—'], ['负向 · MOSS', d.neg_zh || d.neg_moss || '—'],
        ['WAI / NoobAI', d.wai || '—'], ['负向 · WAI', d.neg || '—'],
        ['Pony V6 XL', d.pony || '—'], ['负向 · Pony', d.neg_pony || '—'],
        ['Animagine XL', d.anima || '—'], ['负向 · Animagine', d.neg_anima || '—'],
        ['Krea2（自然语言）', d.krea || '—'],
        ['负向 · Krea2', d.neg_krea || '该模型 CFG=1，负向不生效（需把 KSampler cfg 调到 3 以上才起作用）'],
      ] : [
        ['WAI / NoobAI', d.wai || '—'], ['负向 · WAI', d.neg || '—'],
        ['Pony V6 XL', d.pony || '—'], ['负向 · Pony', d.neg_pony || '—'],
        ['Animagine XL', d.anima || '—'], ['负向 · Animagine', d.neg_anima || '—'],
        ['Krea2（自然语言）', d.krea || '—'],
        ['负向 · Krea2', d.neg_krea || '该模型 CFG=1，负向不生效（需把 KSampler cfg 调到 3 以上才起作用）'],
      ]);
      stopWait(); toast('完成' + (d.note ? '（' + d.note + '）' : ''));
    } catch (e) { toast('生成失败：' + e.message); }
  }
  async function doMoss() {
    if (!S.global.length && !S.chars.length) {
      const src = draftText() || ($('#nl').value || '').trim();
      if (!src) { toast('先写描述或选标签'); return; }
      toast('自动拆解后生成…');
      try {
        const d = await api('/api/parse', { text: src });
        S.chars = (d.chars || []).map(c => {
          const nm = c.zh || c.name || '';
          return { name: nm, desc: c.desc || '', tags: (c.features || []).map((z, i) => ({ zh: z, en: (c.features_en || [])[i] || z, w: 1 })) };
        });
        (d.tags || []).forEach(t => {
          const x = S.lib.find(e => e.en === t.en || e.en === t.tag);
          const zh = (x && x.zh) || t.zh || '';
          if (zh && !S.global.some(g => g.en === (t.en || t.tag))) S.global.push({ zh, en: t.en || t.tag, w: 1 });
        });
        renderSel();
      } catch (e) { toast('拆解失败：' + e.message); return; }
    }
    const tags = S.global.map(t => ({ tag: t.en, weight: t.w }));
    const stopWait2 = toastSticky('生成草稿中…');
    try {
      const d = await api('/api/generate', {
        tags: tags, chars: buildChars(),
        ai: false, density: $('#selDensity').value, nsfw: S.nsfw,
        polishMode: $('#selPolish') ? $('#selPolish').value : 'api',
        neg: $('#selNeg') ? $('#selNeg').value : 'full',
        use: { wai: 0, pony: 0, moss: 1 }, only: 'moss',
      });
      if (!d.moss) { toast('没有内容'); return; }
      showResult([['MOSS 中文', d.moss], ['负向 · MOSS', d.neg_zh || d.neg_moss || '—']]);
      stopWait2(); toast('已生成到结果栏');
    } catch (e) { toast('失败：' + e.message); }
  }

  /* ===================== 历史 ===================== */
  function saveHist(text) {
    if (!text) return;
    const a = LS.get('hist', []);
    a.unshift({ t: new Date().toLocaleTimeString('zh-CN', { hour12: false }), text });
    LS.set('hist', a.slice(0, 30)); renderHist();
  }
  function renderHist() {
    const box = $('#histBody');
    const a = LS.get('hist', []);
    if (!a.length) { box.innerHTML = '<div class="note">还没有扩写记录</div>'; return; }
    box.innerHTML = a.map((h, i) => `<div class="hist" data-h="${i}">
      <div class="ht">扩写 · ${esc(h.t)}</div>
      <div class="hx">${esc(h.text.slice(0, 70))}…</div></div>`).join('');
    box.querySelectorAll('.hist').forEach(el => el.onclick = () => {
      $('#draft').value = a[+el.dataset.h].text;
      toast('已回填到草稿');
    });
  }

  /* ===================== 图反推 ===================== */
  function initReverse() {
    const drop = $('#dropImg'), file = $('#fileImg');
    drop.onclick = () => file.click();
    file.onchange = () => { if (file.files && file.files[0]) doReverse(file.files[0]); };
    drop.ondragover = e => { e.preventDefault(); drop.style.borderColor = '#5a95f7'; };
    drop.ondragleave = () => drop.style.borderColor = '';
    drop.ondrop = e => {
      e.preventDefault(); drop.style.borderColor = '';
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) doReverse(f);
    };
  }
  function doReverse(file) {
    if (!/^image\//.test(file.type)) { toast('请选择图片文件'); return; }
    const img = new Image();
    img.onload = () => toast('已选图片 ' + file.name + '（' + img.width + '×' + img.height + '）');
    img.src = URL.createObjectURL(file);
    const fd = new FormData();
    fd.append('image', file);
    toast('反推中…（WD14 打标，稍等）');
    const polish = '0';
    fetch('/api/reverse_upload?polish=' + polish, { method: 'POST', body: fd })
      .then(r => r.json())
      .then(d => {
        if (d.error) { toast('反推失败：' + d.error); return; }
        const tags = d.tags || [];
        // 若反推结果含 NSFW 标签，自动打开开关，否则会被过滤
        const hasNsfw = tags.some(t => {
          const lib = S.lib.find(e => e.en === t.en);
          return lib && lib.nsfw;
        });
        if (hasNsfw && !S.nsfw) {
          S.nsfw = true;
          const cb = $('#cbNsfw');
          if (cb) cb.checked = true;
          renderCats();
          toast('检测到 NSFW 标签，已自动打开 NSFW 开关');
        }
        let added = 0;
        tags.forEach(t => {
          const lib = S.lib.find(e => e.en === t.en);
          const zh = (lib && lib.zh) || t.zh || t.en;
          if (lib) { addTag(lib.en); added++; }
          else if (zh && !S.global.some(g => g.en === t.en)) { S.global.push({ zh, en: t.en, w: 1 }); added++; }
        });
        renderSel();
        const text = (d.text || '').trim();
        if (text) { $('#nl').value = text; }
        toast('反推完成：' + added + ' 个标签已加入已选');
      })
      .catch(e => toast('反推失败：' + e.message));
  }

  /* ===================== API 配置 ===================== */
  async function openApi() {
    let old = LS.get('apiCfg', { url: 'https://api.deepseek.com', model: 'deepseek-chat', key: '' });
    try {
      const srv = await api('/api/config');
      if (srv && (srv.url || srv.model)) {
        old = { url: srv.url || old.url, model: srv.model || old.model, key: srv.key || '' };
        old._keySet = !!srv.key_set;
      }
    } catch (e) {}
    openDialog({
      id: 'apiDlg',
      title: '⚙ API 配置',
      fields: [
        { key: 'url', label: 'API 地址', value: old.url },
        { key: 'model', label: '模型', value: old.model },
        { key: 'key', label: 'API Key', value: '', type: 'password', placeholder: old._keySet ? '已配置（显示掩码 ' + old.key + '），留空不改；要换请整串粘贴' : '未配置，请粘贴你的 Key' },
      ],
      okText: '保存',
      onOk: v => {
        const cfg = { url: v.url, model: v.model };
        // 掩码或留空 → 不覆盖已保存的 Key
        const k = (v.key || '').trim();
        if (k && !k.includes('…') && !k.includes('...')) cfg.key = k;
        LS.set('apiCfg', Object.assign({}, LS.get('apiCfg', {}), cfg));
        api('/api/config', cfg).then(() => toast('已保存并同步后端')).catch(() => toast('已保存到本地'));
      },
    });
  }


  /* ===================== 使用手册 ===================== */
  /* 重新设计版：渐变 hero + 实时数据徽章 + 四 Tab（概览 / 流程 / 开关 / 技巧）。
     只留结论，细节用卡片网格承载；窄屏自动单栏，Esc / 遮罩可关。 */
  function openGuide() {
    if ($('#guideDlg')) { $('#guideDlg').style.display = 'flex'; return; }
    if (!$('#guideCss')) {
      const st = document.createElement('style');
      st.id = 'guideCss';
      st.textContent = `
        #guideDlg{position:fixed;inset:0;z-index:999;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(18,26,44,.5);backdrop-filter:blur(3px)}
        #guideDlg *{box-sizing:border-box}
        #guideDlg .gesheet{width:840px;max-width:96vw;max-height:78vh;display:flex;flex-direction:column;background:#fff;border-radius:20px;overflow:hidden;box-shadow:0 26px 70px rgba(20,40,80,.3)}
        #guideDlg .ghero{position:relative;display:flex;align-items:center;gap:18px;padding:22px 46px 22px 26px;color:#fff;background:linear-gradient(135deg,#4c8bf5 0%,#7c5cf5 100%)}
        #guideDlg .ghero:after{content:"";position:absolute;right:-40px;top:-70px;width:220px;height:220px;border-radius:50%;background:rgba(255,255,255,.09)}
        #guideDlg .ghero .gt{font-size:21px;font-weight:800;letter-spacing:.6px;line-height:1.2}
        #guideDlg .ghero .gs{margin-top:7px;font-size:12.5px;opacity:.92;line-height:1.5}
        #guideDlg .gbadges{margin-left:auto;display:flex;gap:9px;position:relative;z-index:1}
        #guideDlg .gb{min-width:74px;padding:8px 10px;border-radius:12px;text-align:center;background:rgba(255,255,255,.17);border:1px solid rgba(255,255,255,.26)}
        #guideDlg .gb b{display:block;font-size:17px;font-weight:800;line-height:1.15;font-variant-numeric:tabular-nums}
        #guideDlg .gb span{font-size:10.5px;opacity:.88}
        #guideDlg .gx{position:absolute;top:13px;right:15px;width:24px;height:24px;line-height:23px;text-align:center;border-radius:8px;cursor:pointer;color:#fff;opacity:.8;font-size:13px;z-index:2}
        #guideDlg .gx:hover{opacity:1;background:rgba(255,255,255,.18)}
        #guideDlg .gtabs{display:flex;gap:7px;padding:12px 26px;border-bottom:1px solid #eef4fc;background:#fff}
        #guideDlg .gtab{padding:6px 15px;border-radius:999px;border:1px solid #e2ebf8;background:#f8fbfe;color:#8494ab;font-size:12.5px;font-weight:600;cursor:pointer;user-select:none;transition:.15s}
        #guideDlg .gtab:hover{border-color:#bcd7ff;color:#2f6fe0}
        #guideDlg .gtab.on{background:linear-gradient(135deg,#5a95f7,#7a5df5);border-color:transparent;color:#fff;box-shadow:0 5px 14px rgba(76,139,245,.3)}
        #guideDlg .gbody{flex:1;min-height:0;overflow:auto;padding:16px 26px 4px;background:#fbfdff}
        #guideDlg .gpanel{display:none}
        #guideDlg .gpanel.on{display:block}
        #guideDlg .glead{padding:14px 16px;border-radius:14px;background:linear-gradient(120deg,#f2f7ff,#f8f5ff);border:1px solid #e4ecfb;margin-bottom:16px}
        #guideDlg .glead-t{font-size:14px;font-weight:700;color:#27364f;line-height:1.55}
        #guideDlg .glead-t b{color:#4c6bf5}
        #guideDlg .glead-s{margin-top:5px;font-size:12px;color:#66799a;line-height:1.6}
        #guideDlg .gtitle{font-size:12px;font-weight:700;color:#8ba0bd;letter-spacing:1.2px;margin:0 0 10px}
        #guideDlg .ggrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(224px,1fr));gap:12px;margin-bottom:4px}
        #guideDlg .gk{padding:13px 15px;border:1px solid #e8f0fb;border-radius:14px;background:#fff;box-shadow:0 2px 10px rgba(40,80,150,.05)}
        #guideDlg .gk.hi{border-left:3px solid #4c8bf5;background:linear-gradient(135deg,#f8fbff,#fdfbff)}
        #guideDlg .gk h4{margin:0 0 6px;display:flex;align-items:center;gap:7px;font-size:13.5px;color:#27364f;line-height:1.4}
        #guideDlg .gk h4 .gi{font-size:14px;line-height:1}
        #guideDlg .gk p{margin:0;font-size:12px;color:#5f7290;line-height:1.72}
        #guideDlg .gk p b{color:#3a72d4}
        #guideDlg .gmini{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin:7px 0 7px}
        #guideDlg .gmini span{padding:2px 8px;border-radius:999px;background:#eef4ff;color:#3a72d4;font-size:11px;font-weight:600;white-space:nowrap}
        #guideDlg .gmini i{color:#b9c9e2;font-style:normal;font-size:11px}
        #guideDlg .gsteps{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin-bottom:6px}
        #guideDlg .gsteps span{padding:4px 12px;border-radius:999px;background:#fff;border:1px solid #dbe7ff;color:#3a72d4;font-size:12px;font-weight:600}
        #guideDlg .gsteps i{color:#b9c9e2;font-style:normal}
        #guideDlg .ghint{margin:0 0 16px;font-size:11.5px;color:#93a5c0;line-height:1.6}
        #guideDlg .grows{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:8px 12px}
        #guideDlg .grow{display:flex;gap:10px;align-items:baseline;padding:7px 11px;border:1px solid #eef4fc;border-radius:10px;background:#fff}
        #guideDlg .grow b{flex:0 0 72px;font-size:12.5px;color:#2f6fe0;white-space:nowrap}
        #guideDlg .grow span{font-size:12px;color:#5f7290;line-height:1.6;min-width:0}
        #guideDlg .gnote{display:flex;gap:8px;padding:8px 12px;margin-bottom:7px;border-radius:10px;background:#fffaf0;border:1px solid #fbe8c4;font-size:12px;color:#8a6a2f;line-height:1.62}
        #guideDlg .gfoot{display:flex;gap:9px;justify-content:flex-end;padding:13px 26px;border-top:1px solid #eef4fc;background:#fff}
        @media (max-width:700px){
          #guideDlg{padding:10px}
          #guideDlg .gesheet{width:100%;max-width:100%;max-height:88vh}
          #guideDlg .ghero{flex-direction:column;align-items:flex-start;gap:13px;padding:18px 18px 16px}
          #guideDlg .ghero .gt{font-size:18px}
          #guideDlg .gbadges{margin-left:0;flex-wrap:wrap;gap:7px;width:100%}
          #guideDlg .gb{flex:1 1 0;min-width:0;padding:7px 5px}
          #guideDlg .gb b{font-size:15px}
          #guideDlg .gtabs{padding:10px 16px;overflow-x:auto}
          #guideDlg .gbody{padding:14px 16px 4px}
          #guideDlg .ggrid,#guideDlg .grows{grid-template-columns:1fr}
          #guideDlg .gfoot{padding:12px 16px}
        }
      `;
      document.head.appendChild(st);
    }
    const lib = (S && S.lib) || [];
    let nChar = 0;
    for (let i = 0; i < lib.length; i++) { const t = lib[i]; if (t && t.cat === '角色') nChar++; }
    const nTag = lib.length;
    const BADGE = (v, k) => `<div class="gb"><b>${v}</b><span>${k}</span></div>`;
    const CARD = (icon, title, steps, desc) => `<div class="gk">
      <h4><span class="gi">${icon}</span>${title}</h4>
      ${steps ? `<div class="gmini">${steps.map(s => `<span>${s}</span>`).join('<i>→</i>')}</div>` : ''}
      <p>${desc}</p></div>`;
    const HI = (title, desc) => `<div class="gk hi"><h4>${title}</h4><p>${desc}</p></div>`;
    const ROW = (k, v) => `<div class="grow"><b>${k}</b><span>${v}</span></div>`;
    const NOTE = t => `<div class="gnote"><span>⚠</span><span>${t}</span></div>`;
    const TAB = [['概览', 0], ['流程', 1], ['开关', 2], ['技巧', 3]];

    const P0 = `
      <div class="glead">
        <div class="glead-t">图反推 → AI 扩写 → 拆标签 → 生成 <b>MOSS / WAI / Pony</b></div>
        <div class="glead-s">全程本机 127.0.0.1:8901 运行，不联网；只有勾选 API 时，文字才会发给 DeepSeek。</div>
      </div>
      <div class="gtitle">三条主路径</div>
      <div class="ggrid" style="margin-bottom:12px">
        ${CARD('🖼️', '图 → 提示词', ['选图反推', '检查标签', '生成'], '丢一张图自动打标，确认标签后一键出结果，最快。')}
        ${CARD('✍️', '文字 → 提示词', ['写描述', 'AI 扩写', '拆标签'], '一句话说清角色，扩写成标准格式，再拆回标签。')}
        ${CARD('🏷️', '标签 → 提示词', ['挑标签', '拖进角色框', '生成'], '词库点选、按角色归位，最精确也最可控。')}
      </div>
      <p class="ghint" style="margin:0"><b style="color:#3a72d4">多角色</b>：一个角色一个框，位置标签拖进对应角色框才绑得住人；图反推常给一堆散标签，记得手动归位。</p>`;

    const P1 = `
      <div class="gsteps"><span>① 反推 / 描述</span><i>→</i><span>② 挑标签</span><i>→</i><span>③ 出结果</span></div>
      <p class="ghint">顶部步骤条只是流程提示，点击不会自动跳转。</p>
      <div class="gtitle">核心按钮速查</div>
      <div class="grows">
        ${ROW('生成结果', '一次出 MOSS + WAI + Pony 及各自负向')}
        ${ROW('AI 扩写', '把描述补成标准格式，同时存进历史')}
        ${ROW('拆成标签', '草稿拆成角色与标签，各归各位')}
        ${ROW('生成 MOSS', '只按「已选」出中文段落与负向')}
        ${ROW('画风库', '50 张缩略图，点一张即加画风标签')}
        ${ROW('反推选图', '上传或拖图，WD14 打标后进「已选」')}
        ${ROW('⚙API', '配置地址、模型、Key，回显为掩码')}
        ${ROW('润色', 'API / 本地 / 模板 / 关，四档')}
        ${ROW('密度', '精简 / 标准 / 复杂，控制标签数量')}
        ${ROW('负向', '完整 / 精简 / 关，控制负向长度')}
      </div>
      <p class="ghint" style="margin:12px 0 0">「生成结果」一次出 6 个区块（三种模型 + 三种负向），每块右上角可单独复制；润色只影响 MOSS 中文段落，WAI / Pony 始终是标签串。</p>`;

    const P2 = `
      <div class="gtitle">三个必须知道的开关</div>
      <div class="ggrid" style="margin-bottom:16px">
        ${HI('NSFW 有两个，别混', '顶部「NSFW模式」控制扩写 / 润色的内容尺度，也决定生成时是否过滤 NSFW 标签；分类栏「NSFW」只控制标签库是否显示。两个不是一回事。')}
        ${HI('润色四档：速度换通顺', '模板 / 关 = 0 秒但生硬，读起来是标签串；API / 本地 = 通顺但慢，本地还占显存，一次约 40–90 秒。')}
        ${HI('密度：标签数量', '精简 8/6 · 标准 18/14 · 复杂 30/24（每角色 / 全局）；只裁 WAI / Pony 的英文标签，MOSS 中文不受影响。')}
      </div>
      <div class="gtitle">注意事项</div>
      ${NOTE('生图前把润色设为「API」或「关」，避免本地模型占显存、拖慢出图。')}
      ${NOTE('词库含成人内容，仅限 18 岁以上使用，请遵守所在地法律与平台规则。')}
      ${NOTE('角色名与作品版权归原作者；生成内容的合规性请自行判断。')}`;

    const P3 = `
      <div class="gtitle">亮点技巧</div>
      <div class="ggrid">
        ${CARD('🎯', '拖拽三用', null, '拖到<b>角色框</b> = 归给该角色；拖到<b>分类芯片</b> = 改分类；拖到<b>垃圾桶</b> = 删除或移出（自定义角色才是真删）。')}
        ${CARD('🖱️', '右键角色卡', null, '直接改外观、作品、英文名，保存到浏览器与服务端，立即生效。')}
        ${CARD('✅', '手动优先', null, '手动加的标签优先于词库自动外观，扩写也不会覆盖你写的发色与瞳色。')}
        ${CARD('💾', '尺寸自动记忆', null, '拖分隔条调好的面板宽度会被记住；拖乱了点底部「重置面板尺寸」即可。')}
        ${CARD('🔗', '权重微调', null, '标签后的 − / + 以 0.1 调权重，范围 0.1–2.0，非 1.0 会写成 (tag:1.2) 形式。')}
        ${CARD('🔍', '搜索够宽', null, '中文名、英文 tag、作品名、别名都能命中；只输作品名会列出该作全部角色。')}
      </div>`;

    const d = document.createElement('div');
    d.id = 'guideDlg';
    d.innerHTML = `<div class="gesheet">
      <div class="ghero">
        <div>
          <div class="gt">提示词工作台</div>
          <div class="gs">图反推 · 扩写 · 拆标签 · 一键出三种模型的提示词</div>
        </div>
        <div class="gbadges" id="guideBadges">
          ${BADGE(nTag || '18357', '词条')}${BADGE(nChar || '3030', '角色')}${BADGE('50', '画风')}${BADGE('3', '模型')}
        </div>
        <div class="gx" id="guideX">✕</div>
      </div>
      <div class="gtabs" id="guideTabs">
        ${TAB.map(([t, i]) => `<div class="gtab${i ? '' : ' on'}" data-tab="${i}">${t}</div>`).join('')}
      </div>
      <div class="gbody">
        <section class="gpanel on" data-tab="0">${P0}</section>
        <section class="gpanel" data-tab="1">${P1}</section>
        <section class="gpanel" data-tab="2">${P2}</section>
        <section class="gpanel" data-tab="3">${P3}</section>
      </div>
      <div class="gfoot">
        <button class="btn" id="guideReset">重置面板尺寸</button>
        <button class="btn primary" id="guideClose">知道了</button>
      </div>
    </div>`;
    document.body.appendChild(d);

    const tabs = [].slice.call(d.querySelectorAll('[data-tab].gtab'));
    const panels = [].slice.call(d.querySelectorAll('.gpanel'));
    const bd = d.querySelector('.gbody');
    const go = i => {
      tabs.forEach(t => t.classList.toggle('on', t.dataset.tab === String(i)));
      panels.forEach(p => p.classList.toggle('on', p.dataset.tab === String(i)));
      if (bd) bd.scrollTop = 0;
    };
    tabs.forEach(t => { t.onclick = () => go(t.dataset.tab); });

    const close = () => { d.style.display = 'none'; go(0); };
    d.querySelector('#guideClose').onclick = close;
    d.querySelector('#guideX').onclick = close;
    d.onclick = ev => { if (ev.target === d) close(); };
    document.addEventListener('keydown', ev => {
      if (ev.key === 'Escape' && d.style.display !== 'none') close();
    });
    const gr = d.querySelector('#guideReset');
    if (gr) gr.onclick = () => {
      localStorage.removeItem('pane');
      ['.lib', '.mid', '.rbot', '.tools'].forEach(sel => { const el = document.querySelector(sel); if (el) el.style.flex = ''; });
      toast('面板尺寸已重置');
    };
    // 徽章：优先用已加载词库；未加载完则异步补数据
    if (!nTag) {
      api('/api/tags').then(r => {
        const ls = (r && r.tags) || [];
        let nc = 0;
        ls.forEach(t => { if (t && t.cat === '角色') nc++; });
        const bs = d.querySelectorAll('#guideBadges .gb b');
        if (bs[0]) bs[0].textContent = ls.length || 18357;
        if (bs[1]) bs[1].textContent = nc || 3030;
      }).catch(() => {});
    }
  }


  /* ---------- 画风库 ---------- */
  async function openStyles() {
    if ($('#styleDlg')) { $('#styleDlg').style.display = 'flex'; return; }
    const d = document.createElement('div');
    d.id = 'styleDlg';
    d.style.cssText = 'position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:999;background:rgba(20,30,50,.45)';
    d.innerHTML = '<div style="width:760px;max-height:84vh;overflow:auto;background:#fff;border-radius:18px;padding:18px 20px">' +
      '<div style="display:flex;align-items:center;margin-bottom:12px"><b style="font-size:15px">🎨 画风库</b>' +
      '<span style="margin-left:auto;color:#b6c3d6;cursor:pointer" id="styleX">✕</span></div>' +
      '<div id="styleGrid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;font-size:12px;color:#8fa3bd">加载中…</div></div>';
    document.body.appendChild(d);
    d.querySelector('#styleX').onclick = () => d.remove();
    try {
      const r = await api('/api/styles');
      const list = r.styles || [];
      d.querySelector('#styleGrid').innerHTML = list.map((it, i) => `
        <div data-si="${i}" style="cursor:pointer;border:1px solid #eef4fc;border-radius:12px;overflow:hidden;background:#fbfdff">
          <div style="aspect-ratio:1/1;background:#f2f6fd center/contain no-repeat url('${String(it.img).replace(/'/g, '%27')}')"></div>
          <div style="padding:6px 8px;color:#41526b;font-weight:600">${esc(it.name)}</div>
          <div style="padding:0 8px 7px;color:#9db0c8;font-size:11px">${esc(it.tag || '')}</div>
        </div>`).join('');
      d.querySelectorAll('[data-si]').forEach(el => el.onclick = () => {
        const it = list[+el.dataset.si];
        if (it.tag && !S.global.some(x => x.en === it.tag)) {
          S.global.push({ zh: it.name, en: it.tag, w: 1 });
          renderSel(); toast('已加入画风：' + it.name);
        }
        d.remove();
      });
    } catch (e) {
      d.querySelector('#styleGrid').textContent = '加载失败：' + e.message;
    }
  }

  /* ===================== 面板拖拽 ===================== */
  function initResize() {
    const p = LS.get('pane', {});
    const applyPane = () => {
      const W = window.innerWidth || document.documentElement.clientWidth || 1200;
      const H = window.innerHeight || 800;
      const maxSide = Math.max(240, W * 0.40);
      const lib = Math.min(p.lib || 0, maxSide);
      const mid = Math.min(p.mid || 0, maxSide);
      if (lib) $('.lib').style.flex = '0 0 ' + lib + 'px';
      if (mid) $('.mid').style.flex = '0 0 ' + mid + 'px';
      if (p.bottom) $('.rbot').style.flex = '0 0 ' + Math.min(p.bottom, H * 0.55) + 'px';
      // 底部两栏按 2:1 比例（忽略旧像素值，避免草稿被挤成一条）
      const _dr = document.querySelector('.draft'), _tl = document.querySelector('.tools');
      if (_dr) _dr.style.flex = '2 1 0';
      if (_tl) _tl.style.flex = '1 1 0';
      // 右侧永远占剩余宽度
      const r = document.querySelector('.right');
      if (r) { r.style.flex = '1 1 0'; r.style.minWidth = '300px'; }
    };
    applyPane();
    window.addEventListener('resize', applyPane);

    document.querySelectorAll('.grip-v').forEach(g => {
      g.onmousedown = ev => {
        ev.preventDefault();
        const a = g.previousElementSibling, b = g.nextElementSibling;
        if (!a || !b) return;
        const parent = a.parentElement;
        const totalW = parent.getBoundingClientRect().width;
        const isRightCol = b.classList.contains('right');
        const isMidCol = b.classList.contains('mid') || b.classList.contains('lib');
        const x0 = ev.clientX;
        const aw = a.getBoundingClientRect().width;
        const bw = b.getBoundingClientRect().width;
        const pairW = aw + bw;
        const MIN_A = 200, MIN_B = 320;
        const move = e => {
          let na = aw + (e.clientX - x0);
          if (isRightCol) {
            // 最右侧只吸收剩余宽度，左列上限 = 容器 - 右列最小宽
            na = Math.min(Math.max(MIN_A, na), totalW - MIN_B - 12);
            a.style.flex = '0 0 ' + na + 'px';
            b.style.flex = '1 1 0';
            b.style.minWidth = '0';
          } else if (isMidCol) {
            na = Math.min(Math.max(MIN_A, na), pairW - MIN_A);
            a.style.flex = '0 0 ' + na + 'px';
            b.style.flex = '0 0 ' + Math.max(MIN_A, pairW - na) + 'px';
          } else {
            na = Math.max(MIN_A, na);
            a.style.flex = '0 0 ' + na + 'px';
          }
        };
        const up = () => {
          document.removeEventListener('mousemove', move);
          document.removeEventListener('mouseup', up);
          const o = LS.get('pane', {});
          const keyOf = el => el.classList.contains('lib') ? 'lib'
            : el.classList.contains('mid') ? 'mid'
            : el.classList.contains('draft') ? 'draft'
            : el.classList.contains('tools') ? 'tools' : '';
          const ka = keyOf(a), kb = keyOf(b);
          if (ka) o[ka] = Math.round(a.getBoundingClientRect().width);
          if (kb) o[kb] = Math.round(b.getBoundingClientRect().width);
          LS.set('pane', o);
        };
        document.addEventListener('mousemove', move);
        document.addEventListener('mouseup', up);
      };
    });
    document.querySelectorAll('.grip-h').forEach(g => {
      g.onmousedown = ev => {
        ev.preventDefault();
        const bot = $('.rbot');
        const y0 = ev.clientY, h0 = bot.getBoundingClientRect().height;
        const move = e => {
          const h = Math.max(140, Math.min(innerHeight * .62, h0 - (e.clientY - y0)));
          bot.style.flex = '0 0 ' + h + 'px';
        };
        const up = () => {
          document.removeEventListener('mousemove', move);
          document.removeEventListener('mouseup', up);
          const o = LS.get('pane', {}); o.bottom = Math.round(bot.getBoundingClientRect().height); LS.set('pane', o);
        };
        document.addEventListener('mousemove', move);
        document.addEventListener('mouseup', up);
      };
    });
  }


  /* ---------- 设置持久化 ---------- */
  function loadSettings() {
    const c = LS.get('settings', {});
    if (c.api !== undefined) $('#swApi').checked = !!c.api;
    if (c.nsfwTop !== undefined && $('#swNsfwTop')) $('#swNsfwTop').checked = !!c.nsfwTop;
    if (c.density) $('#selDensity').value = c.density;
    if (c.neg) $('#selNeg').value = c.neg === 'lite' ? 'simple' : c.neg;
    if (c.polishMode && $('#selPolish')) $('#selPolish').value = c.polishMode;
    if (c.nsfw !== undefined) S.nsfw = !!c.nsfw;
    if (c.favTop !== undefined) S.favTop = !!c.favTop;
  }
  function saveSettings() {
    LS.set('settings', {
      api: $('#swApi').checked,
      nsfwTop: $('#swNsfwTop') ? $('#swNsfwTop').checked : false,
      density: $('#selDensity').value,
      polishMode: $('#selPolish') ? $('#selPolish').value : 'api',
      neg: $('#selNeg').value,
      nsfw: S.nsfw,
      favTop: S.favTop,
    });
  }
  function bindSettings() {
    ['#swApi', '#swNsfwTop', '#selDensity', '#selNeg', '#selPolish'].forEach(sel => {
      const el = document.querySelector(sel);
      if (el) el.addEventListener('change', saveSettings);
    });
  }

  /* ===================== 启动 ===================== */
  function bind() {
    $('#btnParseDraft').onclick = doParse;
    $('#btnMoss').onclick = doMoss;
    $('#btnGen').onclick = doGenerate;
    $('#btnExpand').onclick = doExpand;
    $('#btnCfg').onclick = openApi;
    const gd = document.querySelector('.guide'); if (gd) gd.onclick = openGuide;
    $('#btnClearSel').onclick = () => { S.chars = []; S.global = []; renderSel(); toast('已清空'); };
    $('#btnClearRes').onclick = () => {
      $('#resBody').innerHTML = '<div class="note" style="padding:26px;text-align:center">点「生成结果」后显示</div>';
      toast('结果已清空');
    };
    $('#btnClearHist').onclick = () => { LS.set('hist', []); renderHist(); toast('历史已清空'); };
    $('#btnReset').onclick = () => {
      S.cat = '全部'; S.sub = '全部'; S.q = ''; S.shown = PAGE;
      renderCats(); renderSub(); renderTags(); toast('已重置');
    };

    const sb = $('#searchBox');
    sb.contentEditable = 'true';
    sb.onfocus = () => { if (sb.textContent.indexOf('搜索') >= 0) sb.textContent = ''; };
    let t;
    sb.oninput = () => {
      clearTimeout(t);
      t = setTimeout(() => { S.q = sb.textContent.trim(); S.shown = PAGE; renderTags(); }, 160);
    };

    /* 标签拖进「自然语言框」和「MOSS 草稿」：写中文，不写英文 tag */
    ['#nl', '#draft'].forEach(sel => {
      const box = document.querySelector(sel);
      if (!box) return;
      box.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
      box.addEventListener('drop', e => {
        e.preventDefault();
        let zh = '';
        const p = window.__dragSel;
        if (p) {
          if (p.from === 'g') { const t = S.global[p.j]; zh = t ? t.zh : ''; }
          else { const c = S.chars[p.i]; const t = c && c.tags[p.j]; zh = t ? t.zh : ''; }
        }
        if (!zh) {
          const en = e.dataTransfer.getData('text/plain');
          const t = S.lib.find(x => x.en === en);
          zh = t ? t.zh : en;
        }
        if (!zh) return;
        const s0 = box.selectionStart == null ? box.value.length : box.selectionStart;
        const s1 = box.selectionEnd == null ? box.value.length : box.selectionEnd;
        const before = box.value.slice(0, s0), after = box.value.slice(s1);
        const sep = (!before || /[，,。；;\s]$/.test(before)) ? '' : '，';
        box.value = before + sep + zh + after;
        const pos = (before + sep + zh).length;
        box.selectionStart = box.selectionEnd = pos;
        box.dispatchEvent(new Event('input', { bubbles: true }));
      });
    });

    loadSettings(); bindSettings();
    initResize(); initScroll(); initReverse();
    renderChips(); renderHist(); renderSel();
  }

  async function boot() {
    bind();
    try {
      const d = await api('/api/tags');
      S.lib = d.tags || [];
    } catch (e) {
      toast('词库加载失败：' + e.message);
    }
    const ov = LS.get('catOverrides', {});
    S.catOverrides = (ov && typeof ov === 'object' && !Array.isArray(ov)) ? ov : {};
    mergeCustomChars();                 // 自定义角色：localStorage 与后端（/api/chars）都合并
    renderCats(); renderSub(); renderTags();
  }
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', boot) : boot();
})();
