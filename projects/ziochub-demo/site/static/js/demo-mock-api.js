/* demo-mock-api.js - client-side API mock for static demo */
(function () {
  'use strict';

  const DEMO = {
    dataBase: './data/',
    // Bump version to avoid old cached user/data from previous builds.
    storeKey: 'ziochubDemoState.v9',
  };

  function jsonResponse(obj, status) {
    const body = JSON.stringify(obj);
    return new Response(body, {
      status: status || 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  function textResponse(text, status, contentType) {
    return new Response(String(text || ''), {
      status: status || 200,
      headers: { 'Content-Type': contentType || 'text/plain; charset=utf-8' },
    });
  }

  function ok(obj) {
    return jsonResponse(Object.assign({ success: true }, obj || {}), 200);
  }

  function fail(message, status) {
    return jsonResponse({ success: false, message: message || 'Not implemented in demo' }, status || 200);
  }

  function loadState() {
    try {
      return JSON.parse(localStorage.getItem(DEMO.storeKey) || '{}') || {};
    } catch (e) {
      return {};
    }
  }

  function saveState(s) {
    localStorage.setItem(DEMO.storeKey, JSON.stringify(s || {}));
  }

  async function loadJson(name) {
    const res = await window._demoRealFetch(DEMO.dataBase + name);
    if (!res.ok) throw new Error('Failed to load demo data: ' + name);
    return await res.json();
  }

  function pickDemoUser(users) {
    const st = loadState();
    const u = st && st.user && st.user.username ? st.user : null;
    if (u) return u;
    if (Array.isArray(users) && users.length) {
      // Prefer YAELB as the "logged-in" analyst for the demo.
      const ya = users.find(x => String(x.username || '').toLowerCase() === 'yaelb');
      return ya || users[0];
    }
    return { username: 'yaelb', display_name: 'Yael B', is_admin: false, image: '' };
  }

  async function ensureCache() {
    const st0 = loadState();
    if (st0._cacheReady && st0.users && st0.iocs && st0.campaigns && st0.yara && st0.champs) {
      // Force demo login user to YAELB (requirement: show Yael as the active analyst).
      const ya = Array.isArray(st0.users) ? st0.users.find(x => String(x.username || '').toLowerCase() === 'yaelb') : null;
      if (ya) {
        st0.user = ya;
        saveState(st0);
      }
      return st0;
    }
    const [users, iocs, campaigns, yara, champs] = await Promise.all([
      loadJson('users.json'),
      loadJson('iocs.json'),
      loadJson('campaigns.json'),
      loadJson('yara.json'),
      loadJson('champs.json'),
    ]);
    const user = pickDemoUser(users);
    const next = Object.assign({}, st0, { _cacheReady: true, users, iocs, campaigns, yara, champs, user });
    saveState(next);
    return next;
  }

  function stripUrlProtocol(url) {
    const s = String(url || '').trim();
    return s.replace(/^(?:https?|ftp|sftp):\/\//i, '');
  }

  function uniqSorted(arr) {
    const out = Array.from(new Set((arr || []).filter(Boolean).map(x => String(x).trim()).filter(Boolean)));
    out.sort((a, b) => a.localeCompare(b));
    return out;
  }

  function iocLines(st, type, hashLen) {
    const iocs = (st && st.iocs) ? st.iocs : [];
    return uniqSorted(iocs
      .filter(x => String(x.type || '') === String(type || ''))
      .map(x => String(x.value || '').trim())
      .filter(v => v && (!hashLen || v.length === hashLen)));
  }

  async function handleFeed(url, opts) {
    const u = new URL(url, window.location.href);
    const path = u.pathname || '';
    const method = ((opts && opts.method) || 'GET').toUpperCase();
    if (method !== 'GET') return textResponse('Method not allowed', 405);
    if (!path.startsWith('/feed/')) return textResponse('Not found', 404);

    const st = await ensureCache();
    const seg = path.replace(/^\/feed\//, '').split('/').filter(Boolean);
    const key = seg.join('/');

    if (key === 'ip') return textResponse(iocLines(st, 'IP').join('\n') + '\n');
    if (key === 'domain') return textResponse(iocLines(st, 'Domain').join('\n') + '\n');
    if (key === 'url') return textResponse(iocLines(st, 'URL').join('\n') + '\n');
    if (key === 'email') return textResponse(iocLines(st, 'Email').join('\n') + '\n');

    if (key === 'hash') return textResponse(iocLines(st, 'Hash').join('\n') + '\n');
    if (key === 'md5') return textResponse(iocLines(st, 'Hash', 32).join('\n') + '\n');
    if (key === 'sha1') return textResponse(iocLines(st, 'Hash', 40).join('\n') + '\n');
    if (key === 'sha256') return textResponse(iocLines(st, 'Hash', 64).join('\n') + '\n');

    if (key === 'pa/ip') return textResponse(iocLines(st, 'IP').join('\n') + '\n');
    if (key === 'pa/domain') return textResponse(iocLines(st, 'Domain').join('\n') + '\n');
    if (key === 'pa/url') {
      const vals = iocLines(st, 'URL').map(stripUrlProtocol);
      return textResponse(uniqSorted(vals).join('\n') + '\n');
    }
    if (key === 'pa/md5') return textResponse(iocLines(st, 'Hash', 32).join('\n') + '\n');
    if (key === 'pa/sha256') return textResponse(iocLines(st, 'Hash', 64).join('\n') + '\n');
    if (key === 'pa/email') return textResponse(iocLines(st, 'Email').join('\n') + '\n');

    if (key === 'cp/ip') return textResponse(iocLines(st, 'IP').join('\n') + '\n');
    if (key === 'cp/domain') return textResponse(iocLines(st, 'Domain').join('\n') + '\n');
    if (key === 'cp/url') return textResponse(iocLines(st, 'URL').join('\n') + '\n');
    if (key === 'cp/hash') return textResponse(iocLines(st, 'Hash').join('\n') + '\n');
    if (key === 'cp/md5') return textResponse(iocLines(st, 'Hash', 32).join('\n') + '\n');
    if (key === 'cp/sha1') return textResponse(iocLines(st, 'Hash', 40).join('\n') + '\n');
    if (key === 'cp/sha256') return textResponse(iocLines(st, 'Hash', 64).join('\n') + '\n');

    if (key === 'esa/email') return textResponse(iocLines(st, 'Email').join(','), 200, 'text/plain; charset=utf-8');

    if (key === 'epo/files-list') {
      const tickets = uniqSorted((st.iocs || []).map(x => String(x.ticket_id || '').trim()).filter(Boolean));
      return textResponse(tickets.join('\n') + '\n');
    }

    if (key === 'stix') {
      const objs = (st.iocs || []).slice(0, 2000).map(x => ({
        type: 'indicator',
        name: String(x.value || '').trim(),
        pattern: String(x.value || '').trim(),
        created: x.created_at || new Date().toISOString(),
      })).filter(o => o.name);
      return textResponse(JSON.stringify({ type: 'bundle', objects: objs }, null, 2), 200, 'application/json; charset=utf-8');
    }

    if (key === 'yara-list') {
      const names = uniqSorted((st.yara || []).map(x => String(x.filename || '').trim()).filter(Boolean));
      return textResponse(names.join('\n') + '\n');
    }
    if (seg[0] === 'yara-content' && seg[1]) {
      const filename = seg.slice(1).join('/');
      return window._demoRealFetch('./assets/yara/' + filename, opts);
    }

    return textResponse('Not implemented in demo: ' + path + '\\n', 404);
  }

  function avatarUrlFor(user) {
    if (!user) return null;
    const img = user.image || '';
    if (!img) return './assets/avatars/default.svg';
    return './assets/avatars/' + img;
  }

  function iocToLiveRow(x) {
    // live-stats.js expects keys: ioc, file_type, user, comment, date, country_code
    return {
      ioc: x.value,
      file_type: (x.type || 'Unknown'),
      user: (x.analyst || 'unknown'),
      comment: x.comment || '',
      date: x.created_at || new Date().toISOString(),
      country_code: x.country_code || '',
    };
  }

  function simpleSearch(iocs, q) {
    const query = (q || '').trim().toLowerCase();
    if (!query) return iocs.slice(0, 200);
    return iocs.filter(r => {
      const v = String(r.value || '').toLowerCase();
      const c = String(r.comment || '').toLowerCase();
      const a = String(r.analyst || '').toLowerCase();
      return v.includes(query) || c.includes(query) || a.includes(query);
    }).slice(0, 1000);
  }

  async function handleApi(url, opts) {
    const u = new URL(url, window.location.href);
    const path = u.pathname;
    const method = ((opts && opts.method) || 'GET').toUpperCase();

    const st = await ensureCache();

    // ---- Auth ----
    if (path === '/api/auth/me' && method === 'GET') {
      const user = st.user || pickDemoUser(st.users);
      return ok({
        authenticated: true,
        username: user.username || 'demo',
        display_name: user.display_name || user.username || 'Demo',
        is_admin: false,
        avatar_url: avatarUrlFor(user),
      });
    }
    if (path === '/api/login' && method === 'POST') {
      // Accept any credentials and "log in" as first user.
      const user = pickDemoUser(st.users);
      const next = Object.assign({}, st, { user });
      saveState(next);
      return ok({ message: 'Demo login OK' });
    }
    if (path === '/api/logout' && method === 'POST') {
      const next = Object.assign({}, st);
      delete next.user;
      saveState(next);
      return ok({ message: 'Logged out' });
    }

    function findCampaignNameById(cid) {
      if (cid == null) return '';
      const c = (st.campaigns || []).find(x => Number(x.id) === Number(cid));
      return c ? (c.name || '') : '';
    }

    // ---- Search/browse ----
    if (path === '/api/search' && method === 'GET') {
      const q = u.searchParams.get('q') || '';
      const filtered = simpleSearch(st.iocs || [], q);
      const results = filtered.map((r, idx) => {
        const cid = (r.campaign_id != null) ? Number(r.campaign_id) : null;
        return {
          id: idx + 1,
          file_type: r.type || 'Unknown', // expected by search.js
          ioc: r.value || '',
          date: (r.created_at || '').slice(0, 19).replace('T', ' '),
          user: r.analyst || 'unknown',
          ref: r.ticket_id || '',
          comment: r.comment || '',
          tags: Array.isArray(r.tags) ? r.tags : [],
          campaign_id: cid,
          campaign_name: (r.campaign && String(r.campaign)) ? String(r.campaign) : findCampaignNameById(cid),
          expiration_status: r.expiration || 'Permanent',
          expires_on: null,
          is_expired: false,
          status: 'Active',
          country_code: r.country_code || '',
        };
      });
      return ok({ results, total: results.length });
    }
    if (path === '/api/search/browse-filters' && method === 'GET') {
      // Provide aggregate counts so the browse select works.
      const agg = {};
      (st.iocs || []).forEach(r => {
        const t = String(r.type || '').toLowerCase();
        if (t) agg[t] = (agg[t] || 0) + 1;
      });
      return ok({ aggregates: agg });
    }
    if (path === '/api/ip-country-codes' && method === 'GET') {
      return ok({ countries: [] });
    }

    // ---- Live stats ----
    function normalizeType(t) {
      const x = String(t || '').toLowerCase();
      if (x === 'ip') return 'IP';
      if (x === 'domain') return 'Domain';
      if (x === 'hash') return 'Hash';
      if (x === 'email') return 'Email';
      if (x === 'url') return 'URL';
      return 'Unknown';
    }
    function tldOf(domain) {
      const s = String(domain || '').toLowerCase();
      const parts = s.split('.').filter(Boolean);
      if (parts.length < 2) return '';
      return parts[parts.length - 1];
    }
    function emailDomainOf(email) {
      const s = String(email || '').toLowerCase();
      const at = s.lastIndexOf('@');
      if (at < 0) return '';
      return s.slice(at + 1).trim();
    }
    function campaignNameOfIoc(r) {
      if (r && r.campaign) return String(r.campaign);
      if (r && r.campaign_id != null) return findCampaignNameById(r.campaign_id) || '';
      return '';
    }
    function buildStatsFromIocs(iocs) {
      const stats = { IP: 0, Domain: 0, Hash: 0, Email: 0, URL: 0 };
      const tld_counts = {};
      const email_domain_counts = {};
      const campaign_stats = {};
      (iocs || []).forEach(r => {
        const typ = normalizeType(r.type);
        if (stats[typ] != null) stats[typ] += 1;
        if (typ === 'Domain') {
          const tld = tldOf(r.value);
          if (tld) tld_counts[tld] = (tld_counts[tld] || 0) + 1;
        }
        if (typ === 'Email') {
          const ed = emailDomainOf(r.value);
          if (ed) email_domain_counts[ed] = (email_domain_counts[ed] || 0) + 1;
        }
        const cname = campaignNameOfIoc(r);
        if (cname) campaign_stats[cname] = (campaign_stats[cname] || 0) + 1;
      });
      return { stats, tld_counts, email_domain_counts, campaign_stats };
    }

    if (path === '/api/stats/counts' && method === 'GET') {
      const agg = buildStatsFromIocs(st.iocs || []);
      return ok({ stats: agg.stats, yara_count: (st.yara || []).length });
    }
    if (path === '/api/stats' && method === 'GET') {
      const agg = buildStatsFromIocs(st.iocs || []);
      // Demo country counts: static values so "Top Countries" is never empty.
      // (Real product uses geo enrichment; demo avoids external lookups.)
      const country_counts = {
        us: 148,
        ru: 92,
        cn: 77,
        ir: 44,
        de: 31,
        nl: 26,
        fr: 22,
        gb: 19,
        il: 17,
        ua: 14,
      };
      return ok({
        stats: agg.stats,
        yara_count: (st.yara || []).length,
        // Leaderboards
        campaign_stats: agg.campaign_stats,
        country_counts: country_counts,
        tld_counts: agg.tld_counts,
        email_domain_counts: agg.email_domain_counts,
      });
    }

    // Live feed endpoints used by live-stats.js
    if (path === '/api/recent' && method === 'GET') {
      const limit = parseInt(u.searchParams.get('limit') || '50', 10) || 50;
      const recent = (st.iocs || [])
        .slice()
        .sort((a, b) => Date.parse(b.created_at || '') - Date.parse(a.created_at || ''))
        .slice(0, Math.max(1, Math.min(200, limit)))
        .map(r => ({
          file_type: normalizeType(r.type),
          ioc: r.value,
          value: r.value,
          user: r.analyst || 'unknown',
          analyst: r.analyst || 'unknown',
          comment: r.comment || '',
          date: r.created_at || new Date().toISOString(),
          country_code: r.country_code || '',
          campaign_name: campaignNameOfIoc(r) || '',
          campaign_id: r.campaign_id != null ? Number(r.campaign_id) : null,
        }));
      return ok({ recent });
    }
    if (path === '/api/all-iocs' && method === 'GET') {
      const limit = parseInt(u.searchParams.get('limit') || '500', 10) || 500;
      const iocs = (st.iocs || [])
        .slice()
        .sort((a, b) => Date.parse(a.created_at || '') - Date.parse(b.created_at || ''))
        .slice(-Math.max(1, Math.min(5000, limit)))
        .map(r => ({
          ioc: r.value,
          value: r.value,
          file_type: normalizeType(r.type),
          type: normalizeType(r.type),
          user: r.analyst || 'unknown',
          analyst: r.analyst || 'unknown',
          comment: r.comment || '',
          date: r.created_at || new Date().toISOString(),
          country_code: r.country_code || '',
        }));
      return ok({ iocs });
    }

    // ---- Users (for assign dropdowns) ----
    if (path === '/api/users' && method === 'GET') {
      const users = (st.users || []).map((u, i) => ({
        id: u.id != null ? u.id : (i + 1),
        username: u.username || ('user' + (i + 1)),
        display_name: u.display_name || u.username || ('User ' + (i + 1)),
        avatar_url: avatarUrlFor(u),
        is_admin: false,
      }));
      return ok({ users });
    }

    // ---- Champs (analysis) ----
    if (path === '/api/champs/leaderboard' && method === 'GET') {
      const board = (st.champs && st.champs.leaderboard) ? st.champs.leaderboard : [];
      return ok({ leaderboard: board });
    }
    if (path === '/api/champs/ping' && method === 'POST') return ok({ message: 'pong' });
    if (path === '/api/champs/team-goal' && method === 'GET') return ok({ goal: { target: 1500, title: 'Team goal', message: 'Reach 1,500 IOCs together' } });
    if (path === '/api/champs/team-goal' && method === 'POST') return ok({ message: 'Saved (demo)' });
    if (path === '/api/champs/ticker' && method === 'GET') {
      const custom = (st.champs && Array.isArray(st.champs.ticker_messages)) ? st.champs.ticker_messages : [];
      const banner_direction = (st.champs && st.champs.banner_direction) ? st.champs.banner_direction : 'rtl';
      if (custom.length) {
        return ok({ source: 'custom', banner_direction: banner_direction, messages: custom });
      }
      return ok({
        source: 'system',
        banner_direction: 'rtl',
        messages: [
          { text: 'No recent activity yet.', category: 'team' }
        ]
      });
    }
    if (path === '/api/champs/ticker-messages' && method === 'GET') {
      const custom = (st.champs && Array.isArray(st.champs.ticker_messages)) ? st.champs.ticker_messages : [];
      const banner_direction = (st.champs && st.champs.banner_direction) ? st.champs.banner_direction : 'rtl';
      return ok({ messages: custom, banner_direction: banner_direction });
    }
    if (path === '/api/champs/ticker-messages' && method === 'POST') return ok({ message: 'Saved (demo)' });
    if (path.startsWith('/api/champs/analyst/') && method === 'GET') {
      const uid = path.split('/').pop();
      const byId = (st.champs && st.champs.by_user_id) ? st.champs.by_user_id : {};
      const a = byId && Object.prototype.hasOwnProperty.call(byId, String(uid)) ? byId[String(uid)] : null;
      if (a) {
        // Smart-static rolling window: keep the same points pattern but shift dates to "last 30 days".
        const pattern = Array.isArray(a.activity_points_pattern) ? a.activity_points_pattern : [];
        const teamPattern = Array.isArray(a.team_avg_points_pattern) ? a.team_avg_points_pattern : [];
        if (pattern.length === 30) {
          const out = Object.assign({}, a);
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const activity = [];
          const teamAvg = [];
          for (let i = 29; i >= 0; i--) {
            const d = new Date(today.getTime() - (i * 86400000));
            const dk = d.toISOString().slice(0, 10); // YYYY-MM-DD
            const idx = 29 - i; // 0..29 left->right
            activity.push({ date: dk, points: Number(pattern[idx] || 0) });
            const tv = (teamPattern.length === 30) ? Number(teamPattern[idx] || 0) : 0;
            teamAvg.push({ date: dk, points: tv });
          }
          out.activity_per_day = activity;
          out.team_avg_per_day = teamAvg;
          return ok({ analyst: out });
        }
        return ok({ analyst: a });
      }
      return ok({ analyst: null });
    }

    // ---- Feed Pulse (demo) ----
    if (path === '/api/feed-pulse' && method === 'GET') {
      const nowIso = new Date().toISOString();
      const outgoing = [
        {
          value: 'login-microsoft-portal.online',
          type: 'Domain',
          analyst: 'yaelb',
          expiration: 'Expired',
          reason: 'Expired',
          is_allowlisted: false,
          allowlist_reason: '',
        },
        {
          value: '45.15.143.22',
          type: 'IP',
          analyst: 'eitang',
          expiration: 'Expired',
          reason: 'Expired',
          is_allowlisted: false,
          allowlist_reason: '',
        },
        {
          value: 'support@bank-verify-secure.com',
          type: 'Email',
          analyst: 'tamarf',
          expiration: 'Expired',
          reason: 'Expired',
          is_allowlisted: false,
          allowlist_reason: '',
        },
        {
          value: 'urgent-wire-transfer-request.docm',
          type: 'Hash',
          analyst: 'yaelb',
          expiration: 'Deleted',
          reason: 'Deleted by yaelb (cleanup)',
          is_allowlisted: false,
          allowlist_reason: '',
        },
      ];
      const exclusions = [
        { id: 101, value: '8.8.8.8', type: 'IP', anomaly_type: 'critical_infra', excluded_by: 'yaelb', excluded_at: '2026-04-17T09:22:10Z', is_allowlisted: true, allowlist_reason: 'DNS resolver (demo allowlist)' },
        { id: 102, value: '1.1.1.1', type: 'IP', anomaly_type: 'critical_infra', excluded_by: 'michalm', excluded_at: '2026-04-16T18:03:44Z', is_allowlisted: true, allowlist_reason: 'DNS resolver (demo allowlist)' },
        { id: 103, value: 'localhost', type: 'Domain', anomaly_type: 'internal', excluded_by: 'nira', excluded_at: '2026-04-15T11:40:00Z', is_allowlisted: false, allowlist_reason: '' },
        { id: 104, value: 'corp.internal', type: 'Domain', anomaly_type: 'internal', excluded_by: 'omers', excluded_at: '2026-04-14T07:12:33Z', is_allowlisted: false, allowlist_reason: '' },
        { id: 105, value: '10.0.0.0/8', type: 'IP', anomaly_type: 'private_range', excluded_by: 'oril', excluded_at: '2026-04-13T21:05:12Z', is_allowlisted: false, allowlist_reason: '' },
        { id: 106, value: '192.168.0.0/16', type: 'IP', anomaly_type: 'private_range', excluded_by: 'shirac', excluded_at: '2026-04-13T21:08:55Z', is_allowlisted: false, allowlist_reason: '' },
      ];
      return ok({
        incoming: (st.iocs || []).slice(0, 30).map(r => ({
          value: r.value, type: r.type, analyst: r.analyst, campaign: r.campaign || '', is_allowlisted: false, allowlist_reason: ''
        })),
        outgoing: outgoing,
        anomalies: [],
        exclusions: exclusions,
        total_active: (st.iocs || []).length,
        total_all: (st.iocs || []).length,
        incoming_count: 30,
        outgoing_count: outgoing.length,
        exclusions_count: exclusions.length,
      });
    }

    // ---- Campaigns / YARA ----
    if (path === '/api/campaigns' && method === 'GET') {
      return ok({ campaigns: st.campaigns || [] });
    }
    if (path.startsWith('/api/campaign-graph/') && method === 'GET') {
      const idStr = path.split('/').pop();
      const cid = parseInt(idStr, 10);
      const campaigns = st.campaigns || [];
      const camp = campaigns.find(c => Number(c.id) === cid);
      if (!camp) return ok({ nodes: [], edges: [], activity: { has_active_iocs: true } });
      // Match ZIoCHub real campaign-graph schema (Orchestra layout + column headers + circularImage icons)
      const iocs = (st.iocs || []).filter(r => Number(r.campaign_id) === cid);
      const yaraRules = (st.yara || []).filter(y => Number(y.campaign_id) === cid);

      function emojiSvgDataUri(emoji, bg) {
        const safeBg = (bg || '#475569').replace(/[^#a-fA-F0-9]/g, '');
        const svg =
          "<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'>" +
          "<rect width='80' height='80' rx='40' ry='40' fill='" + safeBg + "'/>" +
          "<text x='40' y='52' text-anchor='middle' font-size='40' font-family=\"'Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji',sans-serif\">" +
          String(emoji || '📋') +
          "</text></svg>";
        return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
      }

      const IOC_TYPE_COLORS = {
        IP: '#0891b2',
        Domain: '#7c3aed',
        URL: '#d97706',
        Email: '#16a34a',
        Hash: '#e11d48',
        YARA: '#eab308',
      };
      const EMOJI_SVGS = {
        IP: emojiSvgDataUri('🛡️', '#0891b2'),
        Domain: emojiSvgDataUri('🌐', '#7c3aed'),
        URL: emojiSvgDataUri('🔗', '#d97706'),
        Email: emojiSvgDataUri('📧', '#16a34a'),
        Hash: emojiSvgDataUri('☣️', '#e11d48'),
        YARA: emojiSvgDataUri('📜', '#ca8a04'),
      };
      const COLUMN_X = { IP: -500, Domain: -250, URL: 0, Email: 250, Hash: 500, YARA: 500 };
      const COLUMN_HEADERS = {
        IP: ['IP Addresses', '#00d4ff'],
        Domain: ['Domains', '#a78bfa'],
        URL: ['URLs', '#f59e0b'],
        Email: ['Emails', '#22c55e'],
        Hash: ['Hashes / YARA', '#f43f5e'],
      };

      function normalizeType(t) {
        const x = String(t || '').toLowerCase();
        if (x === 'ip') return 'IP';
        if (x === 'domain') return 'Domain';
        if (x === 'url') return 'URL';
        if (x === 'email') return 'Email';
        if (x === 'hash') return 'Hash';
        return 'Hash';
      }
      function looksLikeIp(v) { return /^(?:\d{1,3}\.){3}\d{1,3}$/.test(String(v || '').trim()); }
      function ipCountryCode(ip) {
        // Demo-only deterministic mapping for flags (keeps UI similar to real without geo lookup)
        const s = String(ip || '').trim();
        if (!looksLikeIp(s)) return '';
        const last = parseInt(s.split('.').pop(), 10);
        if (!isFinite(last)) return '';
        const codes = ['us','ru','cn','ir','de','nl','fr','gb','il','ua','pl','tr','br','in'];
        return codes[Math.abs(last) % codes.length];
      }

      const now = new Date();
      const active_ioc_count = iocs.length; // demo: treat all as active
      const expired_ioc_count = 0;
      const yara_count = yaraRules.length;
      const has_active_iocs = active_ioc_count > 0;

      const campNodeId = 'camp_' + cid;
      const campLabel = String(camp.name || ('Campaign ' + cid));
      const campLabelShort = campLabel.length > 30 ? (campLabel.slice(0, 30) + '…') : campLabel;
      const hasRef = !!camp.has_reference_image;
      const campBorder = has_active_iocs ? '#ef4444' : '#64748b';
      const campBorderHi = has_active_iocs ? '#f87171' : '#94a3b8';
      const campEmojiBg = has_active_iocs ? '#ef4444' : '#475569';
      const campCircleImage = hasRef ? emojiSvgDataUri('🎯', campEmojiBg) : emojiSvgDataUri('📋', campEmojiBg);

      const nodes = [{
        id: campNodeId,
        label: '<b>' + campLabelShort.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</b>',
        title: (camp.description ? (campLabel + '\n' + String(camp.description || '')) : campLabel),
        shape: 'circularImage',
        image: campCircleImage,
        has_reference_image: hasRef,
        size: 40,
        x: 0, y: 0,
        fixed: { x: true, y: true },
        borderWidth: 3,
        color: { border: campBorder, highlight: { border: campBorderHi } },
        font: {
          multi: 'html',
          vadjust: -140,
          size: 24,
          color: '#ffffff',
          face: 'Segoe UI, sans-serif',
          bold: { color: '#ffffff', size: 24, face: 'Segoe UI, sans-serif' },
        }
      }];
      const edges = [];

      Object.keys(COLUMN_HEADERS).forEach(function(colType) {
        const header = COLUMN_HEADERS[colType];
        const colX = (COLUMN_X[colType] != null) ? COLUMN_X[colType] : 0;
        nodes.push({
          id: 'header_' + colType,
          label: header[0],
          x: colX, y: 85,
          fixed: { x: true, y: true },
          shape: 'text',
          font: { size: 13, color: header[1], face: 'Inter, Segoe UI, sans-serif', bold: { color: header[1], size: 13 } },
        });
      });

      const colY = {};
      function nextY(key, fallbackKey) {
        if (colY[key] == null) colY[key] = (fallbackKey && colY[fallbackKey] != null) ? colY[fallbackKey] : 150;
        const y = colY[key];
        colY[key] += 80;
        return y;
      }

      iocs.slice(0, 220).forEach(function(r, idx) {
        const t = normalizeType(r.type);
        const colX = (COLUMN_X[t] != null) ? COLUMN_X[t] : 400;
        const nodeColor = IOC_TYPE_COLORS[t] || '#94a3b8';
        const val = String(r.value || '');
        const truncated = val.length > 24 ? (val.slice(0, 24) + '…') : val;
        const nodeY = nextY(t);
        const nodeId = 'ioc_' + (r.id != null ? r.id : idx);
        const node = {
          id: nodeId,
          label: truncated,
          title: t + ': ' + val,
          copyValue: val,
          shape: 'circularImage',
          size: 22,
          x: colX, y: nodeY,
          fixed: { x: true, y: true },
          borderWidth: 2,
          color: { border: nodeColor, highlight: { border: '#ffffff' } },
          font: { color: '#e2e8f0', size: 14, face: 'Consolas, monospace', bold: true, vadjust: 0 },
        };
        if (t === 'IP') {
          const cc = ipCountryCode(val);
          node.image = cc ? ('/static/flags/1x1/' + cc + '.svg') : EMOJI_SVGS.IP;
        } else {
          node.image = EMOJI_SVGS[t] || EMOJI_SVGS.Hash;
        }
        nodes.push(node);
        edges.push({
          from: campNodeId,
          to: nodeId,
          color: { color: nodeColor, opacity: 0.5 },
          width: 1.5,
        });
      });

      // YARA nodes placed in Hash/YARA column
      yaraRules.slice(0, 80).forEach(function(rule, idx) {
        const nodeY = nextY('YARA', 'Hash');
        const file = String(rule.filename || 'rule.yar');
        const short = file.length > 20 ? (file.slice(0, 20) + '…') : file;
        const nodeId = 'yara_' + (rule.id != null ? rule.id : idx);
        nodes.push({
          id: nodeId,
          label: short,
          title: 'YARA: ' + file + (rule.comment ? ('\n' + String(rule.comment)) : ''),
          copyValue: file,
          shape: 'circularImage',
          image: EMOJI_SVGS.YARA,
          size: 22,
          x: 500, y: nodeY,
          fixed: { x: true, y: true },
          borderWidth: 2,
          color: { border: '#eab308', highlight: { border: '#fde68a' } },
          font: { color: '#e2e8f0', size: 14, face: 'Consolas, monospace', bold: true, vadjust: 0 },
        });
        edges.push({
          from: campNodeId,
          to: nodeId,
          color: { color: '#fbbf24', opacity: 0.5 },
          width: 1.5,
        });
      });

      return ok({
        nodes,
        edges,
        activity: {
          linked_ioc_count: iocs.length,
          active_ioc_count: active_ioc_count,
          expired_ioc_count: expired_ioc_count,
          yara_count: yara_count,
          has_active_iocs: has_active_iocs,
        },
      });
    }
    if (path === '/api/yara' && method === 'GET') {
      return ok({ rules: st.yara || [] });
    }

    // Fallback for any other /api route:
    return fail('Not implemented in demo: ' + path, 200);
  }

  // Install mock fetch
  window._demoRealFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = (typeof input === 'string') ? input : (input && input.url ? input.url : '');
    try {
      const u = new URL(url, window.location.href);
      if (u.pathname.startsWith('/api/')) {
        return handleApi(u.toString(), init);
      }
      if (u.pathname.startsWith('/feed/')) {
        return handleFeed(u.toString(), init);
      }
    } catch (e) {
      // ignore and fall through
    }
    return window._demoRealFetch(input, init);
  };
})();
