#!/usr/bin/env python3
"""
Build a client-only static demo site for ZIoCHub.

Reads lab inputs from:
- users/users.json (+ avatar images in users/)
- indicators/*.txt (IOC lines)
- indicators/campains.txt (campaign list)
- indicators/*.yar (sample YARA)

Writes output to:
- demo/ziochub-demo/site/...
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "site"

USERS_JSON = REPO_ROOT / "users" / "users.json"
USERS_DIR = REPO_ROOT / "users"
INDICATORS_DIR = REPO_ROOT / "indicators"
TEMPLATES_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"

OUT_DATA = OUT_DIR / "data"
OUT_ASSETS = OUT_DIR / "assets"
OUT_AVATARS = OUT_ASSETS / "avatars"
OUT_YARA = OUT_ASSETS / "yara"
OUT_STATIC = OUT_DIR / "static"


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _render_static_index_html(*, version: str = "DEMO") -> str:
    """
    Take the Flask/Jinja SPA shell (`templates/index.html`) and convert it to a standalone static HTML:
    - inline the only include (`partials/_brand_block.html`)
    - replace url_for('static', ...) with ./static/...
    - replace a few Jinja variables/attrs with demo values
    """
    tpl = _read_text(TEMPLATES_DIR / "index.html")

    # Inline brand block include (only include used in index.html)
    brand = _read_text(TEMPLATES_DIR / "partials" / "_brand_block.html")
    tpl = tpl.replace("{% include 'partials/_brand_block.html' %}", brand)

    # Resolve the avatar_url conditional to a single branch (static demo always has an avatar URL).
    # Keep the `{% if avatar_url %}` branch and drop the `{% else %}` branch to avoid duplicate IDs.
    tpl = re.sub(
        r"\{\%\s*if\s+avatar_url\s*\%\}([\s\S]*?)\{\%\s*else\s*\%\}[\s\S]*?\{\%\s*endif\s*\%\}",
        r"\1",
        tpl,
        flags=re.MULTILINE,
    )

    # Replace version tokens
    tpl = tpl.replace("{{ version }}", version)

    # Replace body data-* attributes that were conditional in Jinja
    tpl = re.sub(r'data-authenticated="\{\{[^"]*\}\}"', 'data-authenticated="1"', tpl)
    tpl = re.sub(r'data-user-id="\{\{[^"]*\}\}"', 'data-user-id="demo"', tpl)
    tpl = re.sub(r'data-mute-sound="\{\{[^"]*\}\}"', 'data-mute-sound="1"', tpl)
    tpl = re.sub(r'data-ambition-popup-disabled="\{\{[^"]*\}\}"', 'data-ambition-popup-disabled="0"', tpl)
    tpl = re.sub(r'data-achievement-popup-disabled="\{\{[^"]*\}\}"', 'data-achievement-popup-disabled="0"', tpl)
    tpl = re.sub(r'data-search-comment-rtl="\{\{[^"]*\}\}"', 'data-search-comment-rtl="0"', tpl)

    # url_for('index') links
    tpl = tpl.replace("{{ url_for('index') }}", "./index.html")

    # Replace url_for static references. Handle both single and double quoted variants.
    tpl = re.sub(
        r"\{\{\s*url_for\(\s*'static'\s*,\s*filename\s*=\s*'([^']+)'\s*\)\s*\}\}",
        r"./static/\1",
        tpl,
    )
    tpl = re.sub(
        r'\{\{\s*url_for\(\s*"static"\s*,\s*filename\s*=\s*"([^"]+)"\s*\)\s*\}\}',
        r"./static/\1",
        tpl,
    )

    # TG_CONFIG: i18nBase is a url_for('static', filename='i18n/') which becomes ./static/i18n/
    # Leave as-is; our replacement above already covers it.

    # Inject demo mock API script BEFORE app.js so app.js wraps our fetch implementation.
    tpl = tpl.replace(
        '<script src="./static/js/app.js"></script>',
        '<script src="./static/js/demo-mock-api.js"></script>\n    <script src="./static/js/app.js"></script>',
    )

    # Strip Jinja comments (best-effort)
    tpl = re.sub(r"\{#.*?#\}", "", tpl, flags=re.DOTALL)

    # If any stray {{ ... }} remains, replace with empty string to keep HTML valid.
    tpl = re.sub(r"\{\{[^}]+\}\}", "", tpl)
    tpl = re.sub(r"\{%[^%]+%\}", "", tpl)
    return tpl


def _write_demo_mock_api_js(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        r"""/* demo-mock-api.js - client-side API mock for static demo */
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
    } catch (e) {
      // ignore and fall through
    }
    return window._demoRealFetch(input, init);
  };
})();
""",
        encoding="utf-8",
    )


@dataclass
class Campaign:
    name: str
    description: str


def parse_campaigns(text: str) -> list[Campaign]:
    # indicators/campains.txt format:
    # Name: X
    # Description: Y
    blocks = re.split(r"\n\s*\n", text.strip(), flags=re.MULTILINE)
    out: list[Campaign] = []
    for b in blocks:
        name = ""
        desc = ""
        for line in b.splitlines():
            line = line.strip()
            if line.lower().startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.lower().startswith("description:"):
                desc = line.split(":", 1)[1].strip()
        if name:
            out.append(Campaign(name=name, description=desc))
    return out


def parse_ioc_txt(text: str) -> list[dict]:
    """
    IOC sample line format (lab):
      <value> # <comment> by <username> <m/d/YYYY> <hh:mm:ss> <AM/PM>
    """
    rows = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" not in line:
            value = line.strip()
            comment = ""
            username = "unknown"
            dt = None
        else:
            value, meta = line.split("#", 1)
            value = value.strip()
            meta = meta.strip()
            m = re.search(r"\bby\s+([a-zA-Z0-9_.-]+)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})\s*(AM|PM)\b", meta, re.IGNORECASE)
            username = (m.group(1).strip().lower() if m else "unknown")
            comment = meta
            dt = None
            if m:
                try:
                    dt = datetime.strptime(f"{m.group(2)} {m.group(3)} {m.group(4).upper()}", "%m/%d/%Y %H:%M:%S %p")
                except ValueError:
                    dt = None
        if not value:
            continue
        rows.append({
            "value": value,
            "comment": comment,
            "analyst": username,
            "created_at": (dt.isoformat() + "Z") if dt else _now_iso(),
        })
    return rows


def classify_ioc(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "Unknown"
    if v.lower().startswith(("http://", "https://", "ftp://", "sftp://")):
        return "URL"
    if "@" in v and "." in v.split("@")[-1]:
        return "Email"
    if re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", v):
        return "IP"
    if re.fullmatch(r"[a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64}|[a-fA-F0-9]{128}", v):
        return "Hash"
    if "." in v and " " not in v and "/" not in v:
        return "Domain"
    return "Unknown"


def main() -> None:
    random.seed(7)

    # Clean output
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_AVATARS.mkdir(parents=True, exist_ok=True)
    OUT_YARA.mkdir(parents=True, exist_ok=True)
    OUT_STATIC.mkdir(parents=True, exist_ok=True)

    # Users
    users = json.loads(_read_text(USERS_JSON))
    if not isinstance(users, list):
        raise SystemExit("users/users.json must be a JSON array")
    usernames = [str(u.get("username") or "").strip().lower() for u in users if str(u.get("username") or "").strip()]
    if not usernames:
        usernames = ["yaelb"]
    # Copy avatar images referenced by users.json (best-effort)
    for u in users:
        img = (u.get("image") or "").strip()
        if not img:
            continue
        src = USERS_DIR / img
        if src.is_file():
            shutil.copy2(src, OUT_AVATARS / img)
    _write_json(OUT_DATA / "users.json", users)

    # Campaigns
    camp_txt = _read_text(INDICATORS_DIR / "campains.txt")
    camps = parse_campaigns(camp_txt)
    # Expand to 20 campaigns if needed (synthetic suffix, keeps your originals intact)
    while len(camps) < 20 and camps:
        base = camps[len(camps) % max(1, min(8, len(camps)))]
        n = len(camps) + 1
        camps.append(Campaign(name=f"{base.name} {n}", description=base.description))
    campaigns_json = [{
        "id": i + 1,
        "name": c.name,
        "description": c.description,
        "dir": "ltr",
        "has_reference_image": False,
    } for i, c in enumerate(camps[:20])]
    _write_json(OUT_DATA / "campaigns.json", campaigns_json)

    # YARA samples
    yara_files = sorted([p for p in INDICATORS_DIR.glob("*.yar") if p.is_file()])
    yara_rows = []
    # Each YARA file should be "approved" and belong to a different analyst (demo requirement).
    # Ensure YAELB has at least one.
    analyst_cycle = list(usernames)
    if "yaelb" in analyst_cycle:
        # Make yaelb first to guarantee at least one file.
        analyst_cycle.remove("yaelb")
        analyst_cycle.insert(0, "yaelb")
    for p in yara_files:
        dst = OUT_YARA / p.name
        shutil.copy2(p, dst)
        analyst = analyst_cycle[len(yara_rows) % len(analyst_cycle)] if analyst_cycle else "yaelb"
        yara_rows.append({
            "filename": p.name,
            "display_name": p.name,
            "analyst": analyst,
            "uploaded_at": _now_iso(),
            "status": "approved",
            "ticket_id": "",
            "comment": "Demo YARA rule",
            "campaign_id": random.choice(campaigns_json)["id"] if campaigns_json else None,
        })
    _write_json(OUT_DATA / "yara.json", yara_rows)

    # IOC TXT files
    ioc_items = []
    for p in sorted([x for x in INDICATORS_DIR.glob("*.txt") if x.is_file() and x.name.lower() != "campains.txt"]):
        ioc_items.extend(parse_ioc_txt(_read_text(p)))

    # Normalize + enrich
    for r in ioc_items:
        r["type"] = classify_ioc(r.get("value") or "")
        # assign random TTL-like expiration (demo only)
        created = r.get("created_at") or _now_iso()
        r["expiration"] = "Permanent"
        r["ticket_id"] = r.get("ticket_id") or ""
        r["tags"] = []
        r["campaign_id"] = None
        r["created_at"] = created

    # Expand to 1000+ by sampling with small variations (keeps everything fake)
    target_n = 1200
    if ioc_items:
        base = list(ioc_items)
        while len(ioc_items) < target_n:
            src = random.choice(base)
            v = src["value"]
            # small, safe variation to avoid exact dupes
            if src["type"] == "Domain":
                v = f"sub{random.randint(1,999)}.{v}"
            elif src["type"] == "IP":
                parts = v.split(".")
                if len(parts) == 4:
                    parts[-1] = str((int(parts[-1]) + random.randint(1, 200)) % 255)
                    v = ".".join(parts)
            elif src["type"] == "URL":
                v = v.rstrip("/") + f"/{random.randint(1,9999)}"
            elif src["type"] == "Email":
                v = v.replace("@", f"+{random.randint(1,999)}@")
            elif src["type"] == "Hash":
                v = v  # keep as-is; demo can include dupes here
            item = dict(src)
            item["value"] = v
            # spread timestamps
            try:
                dt = datetime.fromisoformat(src["created_at"].replace("Z", "+00:00"))
            except Exception:
                dt = datetime.utcnow()
            dt2 = dt + timedelta(minutes=random.randint(1, 30000))
            item["created_at"] = dt2.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            ioc_items.append(item)

    # Normalize analyst assignment so Champs has meaningful points for everyone.
    # Keep original analyst when it matches a known username; otherwise spread across team.
    if ioc_items and usernames:
        known = set(usernames)
        rr = 0
        for it in ioc_items:
            a = str(it.get("analyst") or "").strip().lower()
            if a not in known:
                it["analyst"] = usernames[rr % len(usernames)]
                rr += 1

        # Guarantee minimum volume per analyst (demo feel): top up by reassigning some items.
        min_per_user = 60
        counts = {u: 0 for u in usernames}
        for it in ioc_items:
            a = str(it.get("analyst") or "").strip().lower()
            if a in counts:
                counts[a] += 1
        # Reassign from the most common analyst to those underfilled
        def most_common_user():
            return max(counts.items(), key=lambda kv: kv[1])[0]
        donor = most_common_user()
        for u in usernames:
            need = max(0, min_per_user - counts.get(u, 0))
            if need <= 0:
                continue
            moved = 0
            for it in ioc_items:
                if moved >= need:
                    break
                if str(it.get("analyst") or "").strip().lower() == donor:
                    it["analyst"] = u
                    moved += 1
            counts[u] = counts.get(u, 0) + moved
            counts[donor] = max(0, counts.get(donor, 0) - moved)

    # Attach campaigns so EVERY campaign has linked IOCs (for graph + champs badges)
    if campaigns_json and ioc_items:
        # Ensure coverage: at least N IOCs per campaign, then add some extra random links.
        per_campaign = 25
        pool = list(ioc_items)
        random.shuffle(pool)
        pos = 0
        for camp in campaigns_json:
            for _ in range(per_campaign):
                if pos >= len(pool):
                    break
                pool[pos]["campaign_id"] = camp["id"]
                pos += 1
        # Extra links
        for item in random.sample(ioc_items, k=min(250, len(ioc_items))):
            if item.get("campaign_id") is None:
                item["campaign_id"] = random.choice(campaigns_json)["id"]

    # Denormalize campaign name for UI convenience (many frontend tables expect a campaign string)
    if campaigns_json and ioc_items:
        cmap = {c["id"]: c["name"] for c in campaigns_json}
        for item in ioc_items:
            cid = item.get("campaign_id")
            item["campaign"] = cmap.get(cid, "") if cid is not None else ""

    _write_json(OUT_DATA / "iocs.json", ioc_items[:target_n])

    # ---------------------------------------------------------------------
    # Champs static dataset (for Champs Analysis spotlight + leaderboard)
    # ---------------------------------------------------------------------
    # Build per-analyst activity for last 30 days based on IOC and YARA timestamps.
    # Points model (demo-only):
    # - IOC submission: 10 points
    # - IOC linked to campaign: +5 points
    # - Approved YARA: 50 points
    from collections import defaultdict
    from datetime import date as _date

    def _parse_iso_z(s: str) -> datetime | None:
        try:
            if not s:
                return None
            ss = str(s).replace("Z", "+00:00")
            return datetime.fromisoformat(ss)
        except Exception:
            return None

    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)) for i in range(29, -1, -1)]
    day_keys = [d.isoformat() for d in days]

    # user_id mapping
    user_id_by_username: dict[str, int] = {}
    for i, u in enumerate(users):
        uname = str(u.get("username") or "").strip().lower()
        if not uname:
            continue
        user_id_by_username[uname] = int(u.get("id") or (i + 1))

    # IOC aggregates
    ioc_total = defaultdict(int)
    ioc_linked = defaultdict(int)
    ioc_points_per_day = defaultdict(lambda: defaultdict(int))
    for it in ioc_items[:target_n]:
        uname = str(it.get("analyst") or "").strip().lower() or "unknown"
        ioc_total[uname] += 1
        if it.get("campaign_id") is not None:
            ioc_linked[uname] += 1
        dt = _parse_iso_z(str(it.get("created_at") or ""))
        if dt:
            dk = dt.date().isoformat()
            if dk in ioc_points_per_day[uname]:
                ioc_points_per_day[uname][dk] += 10 + (5 if it.get("campaign_id") is not None else 0)

    # YARA aggregates
    yara_total = defaultdict(int)
    yara_points_per_day = defaultdict(lambda: defaultdict(int))
    for yr in yara_rows:
        uname = str(yr.get("analyst") or "").strip().lower() or "unknown"
        yara_total[uname] += 1
        dt = _parse_iso_z(str(yr.get("uploaded_at") or ""))
        if dt:
            dk = dt.date().isoformat()
            if dk in yara_points_per_day[uname]:
                yara_points_per_day[uname][dk] += 50

    # Compose leaderboard + spotlight objects
    leaderboard = []
    by_user_id = {}
    for i, u in enumerate(users):
        uname = str(u.get("username") or "").strip().lower()
        if not uname:
            continue
        uid = user_id_by_username.get(uname, i + 1)
        display = u.get("display_name") or u.get("username") or uname
        role_desc = u.get("role") or u.get("description") or ""
        total_i = int(ioc_total.get(uname, 0))
        linked_i = int(ioc_linked.get(uname, 0))
        total_y = int(yara_total.get(uname, 0))
        score = total_i * 10 + linked_i * 5 + total_y * 50
        if score <= 0:
            # Hard static fallback so demo is never empty
            score = 250 + (max(0, (len(users) - i)) * 35)
            total_i = max(total_i, 12 + (len(users) - i) * 4)
            total_y = max(total_y, 1 if uname == "yaelb" else 0)

        # Activity per day
        apd = []
        for dk in day_keys:
            pts = int(ioc_points_per_day[uname].get(dk, 0)) + int(yara_points_per_day[uname].get(dk, 0))
            apd.append({"date": dk, "points": pts})

        # Team average per day
        team_avg = []
        for dk in day_keys:
            total_pts = 0
            for u2 in usernames:
                total_pts += int(ioc_points_per_day[u2].get(dk, 0)) + int(yara_points_per_day[u2].get(dk, 0))
            avg = int(round(total_pts / max(1, len(usernames))))
            team_avg.append({"date": dk, "points": avg})

        # If the last-30-days window has no events (common in demos), generate a deterministic
        # non-zero pattern so the chart is always "alive" while remaining stable across builds.
        if all(int(x.get("points") or 0) == 0 for x in apd):
            seed = sum(ord(c) for c in uname) + int(score)
            pattern = []
            for j in range(30):
                # baseline varies per analyst, with weekly cadence + a couple spikes
                base = 8 + ((seed + j * 17) % 10)  # 8..17
                weekly = 0 if (j % 7) not in (1, 2, 3, 4) else (4 + ((seed + j) % 6))  # workdays heavier
                spike = 0
                if j in (6, 13, 20, 27):
                    spike = 18 + ((seed + j) % 18)  # 18..35
                points = base + weekly + spike
                # keep yaelb slightly more active
                if uname == "yaelb":
                    points += 6
                pattern.append(int(points))
            for j, dk in enumerate(day_keys):
                apd[j]["points"] = pattern[j]

        if all(int(x.get("points") or 0) == 0 for x in team_avg):
            # Simple team avg derived from analyst apd (keeps it non-zero and consistent)
            for j, dk in enumerate(day_keys):
                team_avg[j]["points"] = int(round(apd[j]["points"] * 0.62))

        # Streak (simple): consecutive days with >0 points from the end
        streak = 0
        for row in reversed(apd):
            if row["points"] > 0:
                streak += 1
            else:
                break

        badges = []
        if linked_i >= 1:
            badges.append("team_player")
        if linked_i >= 10:
            badges.append("campaign_master")
        if total_y >= 1:
            badges.append("yara_rookie")
        if total_y >= 3:
            badges.append("yara_master")
        if total_y >= 8:
            badges.append("yara_legend")
        if streak >= 5:
            badges.append("on_fire")
        elif streak >= 3:
            badges.append("warm_streak")

        # Level model (demo): every 500 points is a level
        level = max(1, int(score // 500) + 1)
        xp_in_level = int(score % 500)
        level_width = 500
        xp_to_next = level_width - xp_in_level

        # Store the "shape" of activity as a pattern (30 values). Dates will be shifted at runtime
        # so the chart always shows the last 30 days regardless of when the demo is opened.
        activity_points_pattern = [int(x.get("points") or 0) for x in apd]
        team_avg_points_pattern = [int(x.get("points") or 0) for x in team_avg]

        analyst_obj = {
            "user_id": uid,
            "username": u.get("username") or uname,
            "display_name": display,
            "analyst": u.get("username") or uname,
            "role_description": role_desc,
            "avatar_url": f"./assets/avatars/{u.get('image')}" if u.get("image") else "./assets/avatars/default.svg",
            "is_active": True,
            "score": int(score),
            "rank": 9999,
            "medal": "",
            "trend": "—",
            "total_iocs": int(total_i),
            "yara_count": int(total_y),
            "deletion_count": 0,
            "streak_days": int(streak),
            "badges": badges,
            "level": int(level),
            "xp_in_level": int(xp_in_level),
            "level_width": int(level_width),
            "xp_to_next": int(xp_to_next),
            "activity_per_day": apd,
            "team_avg_per_day": team_avg,
            "activity_points_pattern": activity_points_pattern,
            "team_avg_points_pattern": team_avg_points_pattern,
            "misp_per_day": [],
        }
        leaderboard.append(analyst_obj)
        by_user_id[str(uid)] = analyst_obj

    leaderboard.sort(key=lambda r: int(r.get("score") or 0), reverse=True)
    for idx, row in enumerate(leaderboard):
        row["rank"] = idx + 1
        row["medal"] = ["🥇", "🥈", "🥉"][idx] if idx < 3 else ""

    # Champs ticker messages (SOC announcements) - static demo content
    ticker_messages = [
        {"text": "שבוע הבא יתקיים PT של חברה חיצונית על סביבת AD. שימו לב להתראות חריגות ועדכנו את צוות הסייבר.", "color": "#fbbf24", "dir": "rtl"},
        {"text": "ברוך הבא לעידו שחזר ממילואים. תעדכנו אותו בהקשרי תחקירים פתוחים.", "color": "#00d4ff", "dir": "rtl"},
        {"text": "על כל חשד לבעיות סטטיות ב‑SIEM (חוסר לוגים/דיליי), לפתוח תקלה ולפנות לצוות סייבר.", "color": "#34d399", "dir": "rtl"},
        {"text": "תזכורת: לא מבצעים block לאינדיקטורים פנימיים בלי double‑check מול הבעלים העסקיים.", "color": "#a78bfa", "dir": "rtl"},
        {"text": "הקשחת MFA: כל חריגה באימותים (impossible travel / token reuse) להעלות כ‑High priority.", "color": "#fb7185", "dir": "rtl"},
        {"text": "שינוי נוהל: IOC עם TTL זמני דורש Ticket ID + הערת reason ברורה.", "color": "#93c5fd", "dir": "rtl"},
        {"text": "אם יש זיהוי של phishing בקבוצות HR/Finance — לתייג 'phishing' ולקשר לקמפיין מתאים.", "color": "#60a5fa", "dir": "rtl"},
        {"text": "בדיקות תחזוקה ב‑EDR הלילה 23:00‑01:00. יתכנו disconnects זמניים.", "color": "#f97316", "dir": "rtl"},
    ]

    _write_json(
        OUT_DATA / "champs.json",
        {
            "leaderboard": leaderboard,
            "by_user_id": by_user_id,
            "ticker_messages": ticker_messages,
            "banner_direction": "rtl",
        },
    )

    # Copy app static assets into demo (so everything lives under demo/)
    if STATIC_DIR.is_dir():
        _copytree(STATIC_DIR, OUT_STATIC)

    # Write demo mock API
    _write_demo_mock_api_js(OUT_STATIC / "js" / "demo-mock-api.js")

    # Render the real UI shell as static HTML
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.html").write_text(_render_static_index_html(version="DEMO"), encoding="utf-8")

    print("Built demo site at:", OUT_DIR)


if __name__ == "__main__":
    main()

