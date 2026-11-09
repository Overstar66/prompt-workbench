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
  const CATNAME = { '自定义': '其他' };
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
              renderCats(); renderSub(); renderTags();
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

  function renderSel() {
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
    const map = [['moss', 'MOSS'], ['wai', 'WAI'], ['pony', 'Pony'], ['exp', '扩写结果']];
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
      const sec = /MOSS/.test(k) ? 'moss' : /WAI/.test(k) ? 'wai' : /Pony/.test(k) ? 'pony' : 'exp';
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
      S.chars = (d.chars || []).map(c => {
        const nm = c.zh || c.tag || '';
        const desc = c.desc || text.split(/[。\n]/).filter(x => x.includes(nm)).join('，');
        const zhs = c.features || [];
        const ens = c.features_en || [];
        return { name: nm, desc, tags: zhs.map((z, i) => ({ zh: z, en: ens[i] || z, w: 1 })) };
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
      toast('扩写完成' + (d.engine ? '（' + d.engine + '）' : ''));
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
    const stopWait = toastSticky('生成中…（含本地润色，预计 40-90 秒）');
    try {
      const wantMoss = S.sec.moss !== false;
      const d = await api('/api/generate', {
        tags: S.global.map(t => ({ tag: t.en, weight: t.w })), chars: buildChars(),
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
      ] : [
        ['WAI / NoobAI', d.wai || '—'], ['负向 · WAI', d.neg || '—'],
        ['Pony V6 XL', d.pony || '—'], ['负向 · Pony', d.neg_pony || '—'],
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
    const stopWait2 = toastSticky('生成草稿中…（含本地润色）');
    try {
      const d = await api('/api/generate', {
        tags: S.global.map(t => ({ tag: t.en, weight: t.w })), chars: buildChars(),
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
  /* 内容按页面结构分节（① 概述 → ⑨ FAQ），顶部锚点按钮用 scrollIntoView 跳章。
     只写界面真实现状：实测不生效的开关（英文锚点 / 密度）如实标注「预留」。 */
  function openGuide() {
    if ($('#guideDlg')) { $('#guideDlg').style.display = 'flex'; return; }
    const B = t => `<b style="color:#27364f">${t}</b>`;
    const P = t => `<p style="margin:0 0 6px;color:#46586f;font-size:12.5px;line-height:1.85">${t}</p>`;
    const sub = t => `<div style="font-weight:600;font-size:12.5px;color:#2f6fe0;margin:9px 0 3px">${t}</div>`;
    const UL = arr => '<ul style="margin:0;padding-left:18px;color:#46586f;font-size:12.5px;line-height:1.85">' +
      arr.map(x => `<li style="margin:3px 0">${x}</li>`).join('') + '</ul>';
    const NAV = [['g1', '概述'], ['g2', '工具栏'], ['g3', '标签库'], ['g4', '已选'],
                 ['g5', '草稿·历史'], ['g6', '结果'], ['g7', '流程'], ['g8', '注意'], ['g9', 'FAQ']];
    const SECS = [
      ['g1', '① 这是什么',
        P('本地运行的动漫插画提示词工作台，一条链路走完：' + B('图反推 → AI 扩写 → 拆标签 → 生成 MOSS / WAI / Pony 提示词') + '。') +
        UL([
          '词库约 1.1 万条中英对照标签（角色、外形、服装、动作、道具、场景、画风，其中 NSFW 约 4 千条），另有 50 张画风缩略图。',
          '三个出口：' + B('MOSS') + '（中文段落，配 MOSS 系模型）、' + B('WAI / NoobAI') + '、' + B('Pony V6 XL') + '（英文 tag 串），每条都成对给正向与负向。',
          '拼装和生成全在 127.0.0.1:8901 本机完成，不联网；只有勾选「API」或润色选「API」时文字才会发给 DeepSeek。',
          '顶部步骤条 ① 反推 / 描述 → ② 挑标签 → ③ 出结果 只是流程提示，不会自动跳转。',
        ])],
      ['g2', '② 顶部工具栏',
        UL([
          B('API') + '：勾上时「AI 扩写」走 DeepSeek 云端（失败会自动回退 Ollama）；取消则直接用本机 Ollama（离线可用，但更慢）。润色走 API 还是本地，由下面的「润色」下拉决定，跟这个勾选框无关。',
          B('NSFW模式') + '：控制' + B('扩写 / 润色') + '是否生成成人内容。关闭时扩写要求「保持健康内容」，本地润色强制改用安全模型 qwen2.5:7b；它同时决定生成时是否过滤 NSFW 标签、负向是否追加裸露词。',
          B('英文锚点') + '：' + B('预留开关') + '——勾选状态会记进浏览器设置，但当前生成链路没有读取它；现在无论开关如何，英文 tag 都按词库原样输出。',
          B('⚙ API') + '：配置 API 地址、模型名、Key。Key 存在本地（浏览器 localStorage + 服务端 api_config.json），回显为掩码（前 6 位 + 末 4 位）；要换 Key 请整串重新粘贴，掩码不是真实 Key。',
          B('生成结果') + '：按当前「已选」一次性生成 MOSS + WAI + Pony（含各自负向）到右栏。',
        ]) +
        sub('润色 下拉（四档）') +
        UL([
          B('API') + '：调 DeepSeek 把规则拼好的 MOSS 改写成通顺中文段落；不占显存，通常几秒。API 失败或返回为空时不回退本地，结果栏保留规则底稿。',
          B('本地') + '：强制走 Ollama 改写；安全模式用 qwen2.5:7b，NSFW 开着时用 goonsai 3B。占显存，一次约 40–90 秒。',
          B('关') + '：不润色，直接输出标签式 MOSS，最快，但读起来是「标签串」。',
          B('模板') + '：规则模板拼接后直接返回，结果标记「模板拼接」，同样不经过模型。',
          '怎么选：MOSS 想读得顺 → API；要离线 → 本地；赶时间或只关心 WAI / Pony → 关。',
        ]) +
        sub('密度 下拉（精简 / 标准 / 复杂）') +
        UL([
          B('预留参数') + '：当前版本会保存选择，但后端尚未读取它，三档生成结果完全一致（已实测）；设计上用于调节 WAI / Pony 的标签密度。',
        ]) +
        sub('负向 下拉（三档）') +
        UL([
          B('完整') + '：默认。WAI 约 590 字符（画质、手部、解剖、水印、裁切等），Pony 额外带 score_4 / score_5 / score_6 系列。',
          B('精简') + '：只留约 7 项核心负向（约 215 字符），提示词短、可读性好。',
          B('关') + '：不输出负向（空串），适合自己另配负向。',
          '三档都会自适应：正向里已出现裸体 / uncensored / chibi / 单色等词时自动剔除冲突负向；' + B('NSFW模式关闭') + '时追加 nude / naked / topless 等；' + B('只有一个角色') + '时追加 2girls / multiple_girls / split_screen 等防克隆词。',
        ])],
      ['g3', '③ 左栏：标签库',
        UL([
          B('分类芯片') + '：全部 / 角色 / 外形 / 服装 / 动作 / 道具 / 场景 / 其他（即「自定义」）/ 自定义2 / 自定义3，外加你自建的顶级分类；点一下切换。',
          B('子分类芯片') + '：带「▾」的分类会展开第二排。角色 → 游戏 / 动漫 / MOSS原创 / 自定义；动作 → 单人 / 亲密 / 双人互动 / 姿势 / 日常；外形 → 发型 / 发色 / 眼睛 / 表情 / 身体 / 体型；服装 → 上装 / 下装 / 制服 / 连衣裙 / 泳装 / 袜鞋 / 配饰 / 情趣；场景 → 室内 / 室外 / 光线 / 建筑 / 天气 / 时间段；道具 → 日常 / NSFW；其他 → 构图 / 画质 / 风格 / 视角 / 镜头 / 色彩 / 效果。',
          B('搜索') + '：同时匹配中文名、英文 tag、作品名与别名，「迷宫饭」「EVA」「蓝发」「long hair」都能命中；只输作品名会列出该作品的全部角色。',
          B('重置筛选') + '：清空搜索词和分类 / 子分类选择，回到「全部」。',
          B('描述框 + AI 扩写') + '：左上写自然语言，点「AI 扩写」补成标准格式；结果显示在右栏「扩写结果」，同时存进历史。',
          B('自动补场景') + '：描述框下方的勾选框，当前版本尚未接入扩写请求，勾不勾都按模型自己的判断补场景（预留）。',
          B('点此选图反推 或拖图') + '：上传或拖入图片 → WD14 打标 → 命中的标签自动进「已选」，识别原文写进左上描述框；图里带 NSFW 标签时会自动打开标签库的 NSFW 开关。',
          B('标签卡') + '：单击加入「已选」（角色卡 = 直接建角色框）；左下 ★ 收藏，勾上「收藏」后置顶；角色卡右键可编辑（中文名 / 英文 tag / 作品 / 发色发型 / 眼睛 / 服装 / 体型 / 胸围）；自定义角色拖到垃圾桶即删除。',
          B('拖动标签') + '：拖到分类芯片或子分类芯片 = 改分类（只存在浏览器里，不动服务端词库）；拖到「已选」的角色框 = 归给该角色；拖到垃圾桶 = 从当前已选移除（若是自定义角色 / 自定义子分类，则是真删除）。',
          B('画风库') + '：50 张风格缩略图，点一张就把对应画风 tag 加进全局标签。',
          B('收藏') + '：勾上后收藏的标签排在列表最前面。',
          B('NSFW（分类栏）') + '：只控制词库是否显示 NSFW 标签，默认关闭；和顶部「NSFW模式」是两个独立开关。',
          B('垃圾桶') + '：拖标签进来删除或从已选移除，规则见上面的「拖动标签」。',
          B('＋ 新增分类') + '：可建顶级分类（出现在分类芯片里，右键可改名，留空即删除），也可建当前分类下的子分类（双击或右键改名，× 删除）。',
          B('＋ 添加角色') + '：只在「角色」分类出现。中文名必填，英文 tag 自动转小写下划线，可填作品与外观；保存到浏览器 localStorage 并同步服务端 custom_chars.json。',
        ])],
      ['g4', '④ 中栏：已选',
        UL([
          B('角色框') + '：把左侧标签拖进某个角色框 = 这个标签只属于她。在标签库里单击角色卡会直接建一个角色框。框右上 × 删除角色框，标签后的 − / + 调权重（0.1 一档，范围 0.1–2.0）。',
          B('全局标签') + '：不属于任何角色的共享标签，所有角色共用（场景、画风、构图通常放这里）。点卡片上的 − / + 调权重，× 删除单条，区块右上 × 一键清空全部全局标签。',
          B('√ 无冲突 / ⚠ 冲突') + '：每次改动自动检测互斥项 —— 裸体 × 穿衣、室内 × 室外、单人 × 多人、笑 × 哭，多个角色重名也会提示。只提示，不会自动删标签。',
          B('清空') + '：清空全部已选（角色框 + 全局标签）。',
          '权重：1.0 是默认；不等于 1 时，WAI / Pony 里会写成 (tag:1.2) 这种加权形式。',
        ])],
      ['g5', '⑤ 下栏：草稿 + 历史',
        UL([
          B('草稿') + '：可直接编辑的文本区，改完还能再加工。',
          B('拆成标签') + '：调 /api/parse 把草稿（草稿为空时用左上描述框）拆成角色和标签 —— 角色进角色框，场景等进全局标签。',
          B('生成 MOSS') + '：按「已选」生成中文 MOSS 与负向，送到右栏。若已选为空，会先把草稿（或左上描述框）自动拆解再生成。',
          B('历史记录') + '：每次「AI 扩写」的结果都会存一条，最多 30 条；点一条回填到草稿。清空只清历史。',
        ])],
      ['g6', '⑥ 右栏：结果',
        UL([
          B('标签页开关') + '：MOSS / WAI / Pony / 扩写结果 四个 chip，点一下显示或隐藏对应区块；把 MOSS 关掉后，「生成结果」不再生成 MOSS。',
          '「生成结果」会出 6 个区块：MOSS 中文、负向 · MOSS、WAI / NoobAI、负向 · WAI、Pony V6 XL、负向 · Pony。',
          '每个区块右上角「复制」复制该块全文；「扩写结果」还多一个「填入草稿」。',
          B('清空结果') + '：清掉右栏输出，不影响已选和词库。',
        ])],
      ['g7', '⑦ 推荐使用流程',
        sub('路径 A：图 → 提示词（最快）') +
        UL([
          '① 点「点此选图反推」或把图片拖进去，等 WD14 打标完成。',
          '② 检查「已选」：删掉无关标签，把人物标签拖进对应角色框，场景留在全局。',
          '③ 点「生成结果」，在右栏复制 MOSS / WAI / Pony。',
        ]) +
        sub('路径 B：文字 → 提示词') +
        UL([
          '① 左上描述框写自然语言，例：' + B('初音未来：蓝色长双马尾，白色连衣裙，站在窗边，微笑') + '。',
          '② 点「AI 扩写」，右栏「扩写结果」给出标准格式，同时存进历史。',
          '③ 点「填入草稿」→ 按需修改 → 「拆成标签」或「生成 MOSS」。',
        ]) +
        sub('路径 C：纯标签拼装') +
        UL([
          '① 从词库点标签加入「已选」，角色卡会直接建角色框。',
          '② 把外形 / 服装 / 动作标签拖进对应角色框，场景和画风放全局。',
          '③ 点「生成结果」。',
        ]) +
        sub('多角色补充') +
        UL([
          '每个角色一个角色框，标签拖进各自的框；WAI / Pony 会自动加 (2girls:1.45) 这类多角色词。',
          '位置标签（画面左侧 / 正中 / 右侧）也要放进对应角色的框，才能把人和位置绑在一起。',
          '图反推通常只得到一堆散标签，记得手动归位，否则会全进全局标签。',
        ])],
      ['g8', '⑧ 注意事项',
        UL([
          '首次使用先在 ⚙ API 填地址、模型、Key；不填也能用，但扩写和润色只能走本地 Ollama。',
          '本地模型（Ollama）会占显存：生图前把「润色」设为 API 或关，避免和生图抢显存。',
          'NSFW 有两个开关：顶部「NSFW模式」管扩写 / 润色的尺度与生成时的过滤；分类栏「NSFW」只管词库显示。',
          '词库含成人内容，仅限 18 岁以上使用；请遵守所在地法律与平台规则。',
          '角色名与作品版权归原作者；本工具只做提示词整理，生成内容的合规性请自行判断。',
          '面板尺寸会自动记住（拖分隔条调整）；拖乱了点本说明书底部「重置面板尺寸」。',
          '数据存在浏览器 localStorage（收藏、分类改名、自定义角色、设置、历史）+ 服务端 custom_chars.json；清浏览器数据会丢前端那份。',
          '小提示：「生成 MOSS」读的是分类栏的 NSFW 开关，「生成结果」读的是顶部 NSFW模式 —— 发现 MOSS 里 NSFW 内容和预期不符时，先看分类栏那个开关。',
        ])],
      ['g9', '⑨ 常见问题',
        sub('Q1 生成出来为什么是标签串，不是通顺句子？') +
        P('润色选了「模板」或「关」。改成「API」或「本地」重新生成即可；只关心 WAI / Pony 时不受影响。') +
        sub('Q2 为什么角色外观和我的设定不一致？') +
        P('词库里的角色自带外观（发色 / 瞳色 / 服装）。你手动加的同类标签优先，自动外观会跳过对应项；也可以右键角色卡直接改外观并保存。') +
        sub('Q3 图反推结果里有英文没翻译？') +
        P('词库暂缺该词的中文译名，只能原样显示英文 tag；可当普通标签用，或建个自定义分类收纳。') +
        sub('Q4 为什么画不出多个角色？') +
        P('单角色时负向会自动追加 2girls / multiple_girls / split_screen 等防克隆词。要多角色：加多个角色框，每个框放各自标签；仍不行就把负向改成「精简」或「关」。') +
        sub('Q5 服务打不开 / 页面白屏怎么办？') +
        P('确认 8901 端口有 pythonw 在跑（任务管理器看命令行是否含 studio2\\app.py）；没有就用「启动工作台.bat」或手动 pythonw app.py 启动，再刷新 http://127.0.0.1:8901 。') +
        sub('Q6 改了数据要刷新页面吗？') +
        P('标签数据来自 /api/tags，只在页面加载时读一次；改词库文件或服务端角色后请刷新页面。前端新增 / 编辑的角色会立即生效。') +
        sub('Q7 「英文锚点」「密度」调了没反应？') +
        P('这两项当前为预留参数，不影响输出，详见第②节。')],
    ];
    const d = document.createElement('div');
    d.id = 'guideDlg';
    d.style.cssText = 'position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:999;background:rgba(20,30,50,.42);backdrop-filter:blur(2px)';
    d.innerHTML = `<div style="width:780px;max-width:94vw;max-height:92vh;display:flex;flex-direction:column;background:#fff;border-radius:20px;box-shadow:0 24px 70px rgba(20,40,80,.25);overflow:hidden">
      <div style="padding:17px 24px 13px;border-bottom:1px solid #eef4fc;display:flex;align-items:center;gap:10px">
        <div style="font-size:18px">📖</div><div style="font-weight:700;font-size:16px">使用手册</div>
        <div style="color:#9db0c8;font-size:11.5px">提示词工作台 · 完整说明</div>
        <div style="margin-left:auto;color:#b6c3d6;cursor:pointer;font-size:15px" id="guideX">✕</div>
      </div>
      <div id="guideNav" style="padding:10px 24px;border-bottom:1px solid #eef4fc;display:flex;flex-wrap:wrap;gap:6px;background:#fbfdff">
        ${NAV.map(([id, t], i) => `<span class="swchip${i === 0 ? ' on' : ''}" data-go="${id}" style="font-size:12px;cursor:pointer;user-select:none">${t}</span>`).join('')}
      </div>
      <div id="guideBody" style="padding:4px 24px 8px;max-height:70vh;overflow:auto">
        ${SECS.map(([id, t, h]) => `<section id="${id}" style="padding:13px 0 10px;border-bottom:1px dashed #eef4fc">
          <div style="font-weight:700;font-size:14.5px;color:#2f6fe0;margin-bottom:7px">${t}</div>${h}</section>`).join('')}
      </div>
      <div style="padding:12px 24px 16px;border-top:1px solid #eef4fc;display:flex;gap:8px;justify-content:flex-end;background:#fff">
        <button class="btn" id="guideReset" style="height:34px;padding:0 16px">重置面板尺寸</button>
        <button class="btn primary" id="guideClose" style="height:34px;padding:0 22px">知道了</button>
      </div></div>`;
    document.body.appendChild(d);
    const body = d.querySelector('#guideBody');
    const chips = [].slice.call(d.querySelectorAll('[data-go]'));
    chips.forEach(c => c.onclick = () => {
      const t = d.querySelector('#' + c.dataset.go);
      if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
      chips.forEach(x => x.classList.remove('on'));
      c.classList.add('on');
    });
    const close = () => { d.style.display = 'none'; if (body) body.scrollTop = 0; };
    d.querySelector('#guideClose').onclick = close;
    d.querySelector('#guideX').onclick = close;
    d.onclick = ev => { if (ev.target === d) close(); };
    const gr = d.querySelector('#guideReset');
    if (gr) gr.onclick = () => {
      localStorage.removeItem('pane');
      ['.lib', '.mid', '.rbot', '.tools'].forEach(sel => { const el = document.querySelector(sel); if (el) el.style.flex = ''; });
      toast('面板尺寸已重置');
    };
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
    if (p.lib) $('.lib').style.flex = '0 0 ' + p.lib + 'px';
    if (p.mid) $('.mid').style.flex = '0 0 ' + p.mid + 'px';
    if (p.bottom) $('.rbot').style.flex = '0 0 ' + p.bottom + 'px';
    if (p.tools) $('.tools').style.flex = '0 0 ' + p.tools + 'px';

    document.querySelectorAll('.grip-v').forEach(g => {
      g.onmousedown = ev => {
        ev.preventDefault();
        const a = g.previousElementSibling, b = g.nextElementSibling;
        if (!a || !b) return;
        const x0 = ev.clientX, aw = a.getBoundingClientRect().width, bw = b.getBoundingClientRect().width;
        const move = e => {
          const dx = e.clientX - x0;
          a.style.flex = '0 0 ' + Math.max(220, aw + dx) + 'px';
          b.style.flex = '0 0 ' + Math.max(240, bw - dx) + 'px';
        };
        const up = () => {
          document.removeEventListener('mousemove', move);
          document.removeEventListener('mouseup', up);
          const o = LS.get('pane', {});
          const w = Math.round(a.getBoundingClientRect().width);
          if (a.classList.contains('lib')) o.lib = w;
          else if (a.classList.contains('mid')) o.mid = w;
          else if (a.classList.contains('draft')) o.draft = w;
          else o.tools = w;
          o[b.classList.contains('tools') ? 'tools' : 'tools'] = Math.round(b.getBoundingClientRect().width);
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
    if (c.en !== undefined) $('#swEn').checked = !!c.en;
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
      en: $('#swEn').checked,
      nsfwTop: $('#swNsfwTop') ? $('#swNsfwTop').checked : false,
      density: $('#selDensity').value, polishMode: $('#selPolish') ? $('#selPolish').value : 'api',
      neg: $('#selNeg').value,
      polishMode: $('#selPolish') ? $('#selPolish').value : 'api',
      nsfw: S.nsfw,
      favTop: S.favTop,
    });
  }
  function bindSettings() {
    ['#swApi', '#swEn', '#swNsfwTop', '#selDensity', '#selNeg', '#selPolish'].forEach(sel => {
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
