import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Bot,
  Building2,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Globe2,
  Layers3,
  Loader2,
  LogIn,
  LogOut,
  MessageSquareText,
  Play,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Users,
  UserPlus,
  X
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";
const LEAD_API_BASE = import.meta.env.VITE_LEAD_API_BASE || "/lead/v1";
const POLL_INTERVAL_MS = 8000;
const MAX_TOASTS = 4;
const ACTIVE_STATUSES = new Set(["running", "queued", "processing", "extracting", "analyzing"]);
const DEFAULT_ROLES = "CEO, Founder, Owner";
const INDUSTRY_PATTERNS = [
  ["IT", /\b(?:it|information technology)\b/i],
  ["software", /\bsoftware\b/i],
  ["SaaS", /\bsaas\b/i],
  ["construction", /\bconstruction\b/i],
  ["healthcare", /\b(?:healthcare|health care|medical|clinic|clinics|hospital|hospitals)\b/i],
  ["real estate", /\breal estate\b/i],
  ["fintech", /\b(?:fintech|financial technology)\b/i],
  ["cybersecurity", /\b(?:cybersecurity|cyber security)\b/i],
  ["AI", /\b(?:ai|artificial intelligence)\b/i],
  ["ecommerce", /\b(?:ecommerce|e-commerce|online retail)\b/i],
  ["marketing", /\b(?:marketing|advertising)\b/i],
  ["manufacturing", /\bmanufacturing\b/i],
  ["logistics", /\b(?:logistics|transportation|freight)\b/i],
  ["restaurants", /\b(?:restaurant|restaurants|food service)\b/i],
  ["law firms", /\b(?:law firm|law firms|legal)\b/i],
  ["accounting", /\b(?:accounting|bookkeeping|cpa)\b/i],
  ["education", /\b(?:education|school|schools|edtech|training)\b/i],
  ["insurance", /\binsurance\b/i],
  ["retail", /\bretail\b/i],
  ["automotive", /\b(?:automotive|auto repair|car dealer|dealership)\b/i],
  ["dental", /\b(?:dental|dentist|dentists)\b/i],
  ["home services", /\b(?:home services|cleaning|landscaping|pest control)\b/i],
  ["solar", /\bsolar\b/i],
  ["roofing", /\broofing\b/i],
  ["plumbing", /\bplumbing\b/i],
  ["HVAC", /\b(?:hvac|heating|air conditioning)\b/i],
  ["nonprofit", /\b(?:nonprofit|non-profit|charity|charities)\b/i]
];
const COUNTRY_PATTERNS = [
  ["US", /\b(?:us|usa|u\.s\.|u\.s\.a\.|united states|america)\b/i],
  ["UK", /\b(?:uk|u\.k\.|united kingdom|england)\b/i],
  ["Canada", /\bcanada\b/i],
  ["Australia", /\baustralia\b/i],
  ["UAE", /\b(?:uae|u\.a\.e\.|dubai|abu dhabi)\b/i],
  ["Pakistan", /\bpakistan\b/i],
  ["India", /\bindia\b/i],
  ["Germany", /\bgermany\b/i],
  ["France", /\bfrance\b/i]
];
const ROLE_PATTERNS = [
  ["CEO", /\b(?:ceo|chief executive officer)\b/i],
  ["Founder", /\b(?:founder|co-founder|cofounder)\b/i],
  ["Owner", /\bowner\b/i],
  ["CTO", /\b(?:cto|chief technology officer)\b/i],
  ["CFO", /\b(?:cfo|chief financial officer)\b/i],
  ["COO", /\b(?:coo|chief operating officer)\b/i],
  ["CMO", /\b(?:cmo|chief marketing officer)\b/i],
  ["President", /\bpresident\b/i],
  ["Director", /\bdirector\b/i],
  ["Partner", /\bpartner\b/i],
  ["Manager", /\bmanager\b/i]
];
const SUGGESTED_PROMPTS = [
  "Find 5 IT company CEOs in the US",
  "Find 5 construction company CEOs in the US",
  "Find 5 SaaS company founders in the US",
  "Find 5 healthcare company owners in the US",
  "Find 5 real estate company owners in the US",
  "Find 5 fintech company CEOs in the US",
  "Find 5 cybersecurity company CTOs in the US",
  "Find 5 marketing agency owners in the US",
  "Find 5 manufacturing company CEOs in the US",
  "Find 5 logistics company owners in the US",
  "Find 5 restaurant owners in the US",
  "Find 5 law firm partners in the US",
  "Find 5 accounting firm owners in the US",
  "Find 5 dental clinic owners in the US",
  "Find 5 roofing company owners in the US",
  "Find 5 solar company CEOs in the US",
  "Find 5 insurance agency owners in the US",
  "Find 5 ecommerce company founders in the US"
];

function asTime(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function shortId(id) {
  return id ? id.slice(0, 8) : "";
}

function statusLabel(status) {
  return status ? status.charAt(0).toUpperCase() + status.slice(1) : "Unknown";
}

function statusIcon(status) {
  if (status === "completed" || status === "enriched") return <CheckCircle2 size={14} />;
  if (status === "failed") return <AlertCircle size={14} />;
  if (ACTIVE_STATUSES.has(status)) return <Loader2 size={14} className="spin" />;
  return <Clock3 size={14} />;
}

function titleCase(value) {
  if (!value) return "";
  if (["IT", "AI", "SaaS", "UAE", "UK", "US", "HVAC"].includes(value)) return value;
  return value.replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}

function inferIndustry(query, fallback = "general business") {
  const known = INDUSTRY_PATTERNS.find(([, pattern]) => pattern.test(query));
  if (known) return known[0];

  const generic = query.match(
    /\bfind\s+(?:\d+\s+)?(?:top\s+|best\s+)?(.+?)\s+(?:companies|company|businesses|business|firms|firm|agencies|agency|clinics|clinic|restaurants|restaurant|ceos|founders|owners|leads|decision makers)\b/i
  );
  if (!generic) return fallback;

  const industry = generic[1]
    .replace(/\b(?:in|from|near|with|that|have|has|the|a|an)\b.*$/i, "")
    .replace(/\b(?:ceo|ceos|founder|founders|owner|owners|cto|ctos|cfo|cfos|director|directors)\b/gi, "")
    .trim();

  return industry || fallback;
}

function inferCountry(query, fallback = "US") {
  const known = COUNTRY_PATTERNS.find(([, pattern]) => pattern.test(query));
  return known ? known[0] : fallback;
}

function inferRoles(query, fallback = DEFAULT_ROLES) {
  const roles = ROLE_PATTERNS.filter(([, pattern]) => pattern.test(query)).map(([role]) => role);
  return roles.length ? roles.join(", ") : fallback;
}

function inferCount(query, fallback = 10) {
  const match = query.match(
    /\b(\d{1,2})\b(?=[^.,;]{0,70}\b(?:companies|company|businesses|business|firms|firm|agencies|agency|clinics|clinic|restaurants|restaurant|leads|contacts)\b)/i
  );
  if (!match) return fallback;
  return Math.min(50, Math.max(1, Number(match[1]) || fallback));
}

function inferCampaignFields(query, current) {
  const industry = inferIndustry(query, current.industry);
  const country = inferCountry(query, current.country);
  const targetRoles = inferRoles(query, DEFAULT_ROLES);
  const companyCount = inferCount(query, current.company_count);
  const roleForName = targetRoles === DEFAULT_ROLES ? "Companies" : targetRoles.split(",")[0].trim() + "s";

  return {
    name: `${country} ${titleCase(industry)} ${roleForName}`,
    industry,
    country,
    target_roles: targetRoles,
    company_count: companyCount
  };
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("insightflow-ai-token") || "");
  const [mode, setMode] = useState("login");
  const [authForm, setAuthForm] = useState({ email: "user000@example.com", password: "password123" });
  const [activeView, setActiveView] = useState("dashboard");
  const [campaigns, setCampaigns] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [people, setPeople] = useState([]);
  const [providerStatus, setProviderStatus] = useState(null);
  const [campaignForm, setCampaignForm] = useState({
    name: "US SaaS CEOs",
    query: "Find SaaS CEOs in US companies",
    industry: "SaaS",
    country: "US",
    target_roles: "CEO",
    company_count: 10
  });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [toasts, setToasts] = useState([]);

  const isAuthed = Boolean(token);

  const addToast = useCallback((toast) => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current.slice(-(MAX_TOASTS - 1)), { id, kind: "info", ...toast }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 5200);
  }, []);

  const apiRequest = useCallback(
    async (base, path, options = {}) => {
      const headers = new Headers(options.headers || {});
      if (token) headers.set("Authorization", `Bearer ${token}`);
      if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

      const response = await fetch(`${base}${path}`, { ...options, headers });
      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json") ? await response.json() : await response.text();

      if (!response.ok) {
        const detail = typeof data === "object" ? data.detail || data.message || JSON.stringify(data) : data;
        throw new Error(detail || `Request failed with ${response.status}`);
      }
      return data;
    },
    [token]
  );

  const request = useCallback((path, options = {}) => apiRequest(API_BASE, path, options), [apiRequest]);
  const leadRequest = useCallback((path, options = {}) => apiRequest(LEAD_API_BASE, path, options), [apiRequest]);

  const loadLeadData = useCallback(
    async ({ silent = false } = {}) => {
      if (!token) return;
      try {
        const [campaignData, peopleData, providerData] = await Promise.all([
          leadRequest("/campaigns"),
          leadRequest("/leads?limit=300"),
          leadRequest("/provider-status")
        ]);
        const companyGroups = await Promise.all(
          campaignData.slice(0, 40).map((campaign) =>
            leadRequest(`/campaigns/${campaign.id}/companies`).catch(() => [])
          )
        );
        setCampaigns(campaignData);
        setCompanies(companyGroups.flat());
        setPeople(peopleData);
        setProviderStatus(providerData);
        setError("");
      } catch (err) {
        if (!silent) setError(err.message);
      }
    },
    [leadRequest, token]
  );

  useEffect(() => {
    if (!token) return;
    loadLeadData();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") loadLeadData({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [loadLeadData, token]);

  const metrics = useMemo(() => {
    const running = campaigns.filter((campaign) => campaign.status === "running").length;
    const completed = campaigns.filter((campaign) => campaign.status === "completed").length;
    const failed = campaigns.filter((campaign) => campaign.status === "failed").length;
    const reachable = companies.filter((company) => company.website_reachable).length;
    return {
      campaigns: campaigns.length,
      companies: companies.length,
      people: people.length,
      running,
      completed,
      failed,
      reachable
    };
  }, [campaigns, companies, people]);

  const latestCampaign = campaigns[0];
  const latestCampaignCompanies = latestCampaign
    ? companies.filter((company) => company.campaign_id === latestCampaign.id)
    : companies;
  const latestCampaignPeople = latestCampaign
    ? people.filter((person) => person.campaign_id === latestCampaign.id)
    : people;

  async function handleAuth(event) {
    event.preventDefault();
    setBusy("auth");
    setError("");
    try {
      if (mode === "register") {
        await request("/auth/register", { method: "POST", body: JSON.stringify(authForm) });
      }
      const data = await request("/auth/login", { method: "POST", body: JSON.stringify(authForm) });
      localStorage.setItem("insightflow-ai-token", data.access_token);
      setToken(data.access_token);
      addToast({ kind: "success", title: "Signed in", body: authForm.email });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function logout() {
    localStorage.removeItem("insightflow-ai-token");
    setToken("");
    setCampaigns([]);
    setCompanies([]);
    setPeople([]);
    setProviderStatus(null);
    addToast({ title: "Signed out", body: "Session cleared." });
  }

  async function createCampaign(event) {
    event.preventDefault();
    setBusy("campaign");
    setError("");
    try {
      const inferred = inferCampaignFields(campaignForm.query, campaignForm);
      const payload = {
        ...campaignForm,
        ...inferred,
        target_roles: inferred.target_roles
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        company_count: Number(inferred.company_count) || 10
      };
      const campaign = await leadRequest("/campaigns", { method: "POST", body: JSON.stringify(payload) });
      setCampaigns((current) => [campaign, ...current.filter((item) => item.id !== campaign.id)]);
      setActiveView("search");
      addToast({ kind: "success", title: "Search created", body: campaign.name });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function runCampaign(campaignId) {
    setBusy(`run-${campaignId}`);
    setError("");
    try {
      const result = await leadRequest(`/campaigns/${campaignId}/run`, { method: "POST" });
      setCampaigns((current) =>
        current.map((campaign) => (campaign.id === result.campaign.id ? result.campaign : campaign))
      );
      await loadLeadData({ silent: true });
      addToast({ kind: "success", title: "Search started", body: "Companies and people will update as enrichment completes." });
    } catch (err) {
      setError(err.message);
      await loadLeadData({ silent: true });
    } finally {
      setBusy("");
    }
  }

  if (!isAuthed) {
    return (
      <div className="auth-page">
        <AuthPanel
          mode={mode}
          setMode={setMode}
          form={authForm}
          setForm={setAuthForm}
          busy={busy === "auth"}
          error={error}
          onSubmit={handleAuth}
        />
        <ToastStack toasts={toasts} onDismiss={(id) => setToasts((items) => items.filter((item) => item.id !== id))} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} setActiveView={setActiveView} onLogout={logout} />
      <main className="workspace">
        <AppHeader
          activeView={activeView}
          onRefresh={() => loadLeadData()}
          busy={busy}
        />

        {error && (
          <div className="error-banner" role="alert">
            <AlertCircle size={17} />
            {error}
          </div>
        )}

        {activeView === "dashboard" && (
          <DashboardView
            metrics={metrics}
            campaigns={campaigns}
            companies={companies}
            people={people}
            providerStatus={providerStatus}
            onOpenSearch={() => setActiveView("search")}
            onRun={runCampaign}
            busy={busy}
          />
        )}

        {activeView === "search" && (
          <SearchView
            campaignForm={campaignForm}
            setCampaignForm={setCampaignForm}
            providerStatus={providerStatus}
            campaigns={campaigns}
            busy={busy}
            onCreate={createCampaign}
            onRun={runCampaign}
          />
        )}

        {activeView === "companies" && (
          <CompaniesView companies={companies} campaigns={campaigns} />
        )}

        {activeView === "people" && (
          <PeopleView people={people} companies={companies} campaigns={campaigns} />
        )}

        {activeView === "process" && (
          <ProcessView latestCampaign={latestCampaign} companies={latestCampaignCompanies} people={latestCampaignPeople} />
        )}
      </main>

      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((items) => items.filter((item) => item.id !== id))} />
    </div>
  );
}

function Sidebar({ activeView, setActiveView, onLogout }) {
  const items = [
    ["dashboard", "Dashboard", BarChart3],
    ["search", "Search", MessageSquareText],
    ["companies", "Companies", Building2],
    ["people", "People", Users],
    ["process", "Process", Layers3]
  ];

  return (
    <aside className="sidebar">
      <div className="product-mark">
        <div className="brand-mark">
          <Sparkles size={22} />
        </div>
        <div>
          <strong>Lead Studio</strong>
          <span>InsightFlow AI</span>
        </div>
      </div>

      <nav className="side-nav" aria-label="Workspace sections">
        {items.map(([id, label, Icon]) => (
          <button key={id} className={activeView === id ? "active" : ""} onClick={() => setActiveView(id)} type="button">
            <Icon size={18} />
            {label}
          </button>
        ))}
      </nav>

      <button className="logout-button" onClick={onLogout} type="button">
        <LogOut size={17} />
        Sign out
      </button>
    </aside>
  );
}

function AppHeader({ activeView, onRefresh, busy }) {
  const titles = {
    dashboard: ["Lead generation dashboard", "Find companies, enrich decision makers, and review website signals."],
    search: ["Company search", "Start a targeted campaign from a natural-language request."],
    companies: ["Company intelligence", "Review discovered websites, reachability, and verification quality."],
    people: ["Decision makers", "Review enriched people and open available LinkedIn profiles."],
    process: ["Workflow process", "Campaign execution from market query to enriched contacts."]
  };
  const [title, subtitle] = titles[activeView] || titles.dashboard;

  return (
    <header className="workspace-header">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="header-actions">
        <button className="icon-button" onClick={onRefresh} title="Refresh data" type="button">
          <RefreshCw size={17} className={busy === "refresh" ? "spin" : ""} />
        </button>
      </div>
    </header>
  );
}

function AuthPanel({ mode, setMode, form, setForm, busy, error, onSubmit }) {
  return (
    <section className="auth-panel">
      <div className="auth-copy">
        <div className="brand-mark large">
          <Sparkles size={32} />
        </div>
        <h1>Lead Studio</h1>
        <p>InsightFlow AI workspace for market search, company intelligence, and decision-maker enrichment.</p>
      </div>
      <form onSubmit={onSubmit} className="auth-form">
        <div className="segmented" role="tablist" aria-label="Authentication mode">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            <LogIn size={16} />
            Login
          </button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
            <UserPlus size={16} />
            Register
          </button>
        </div>
        <label>
          Email
          <input type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} required />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} minLength={6} required />
        </label>
        {error && <div className="error-banner compact"><AlertCircle size={17} />{error}</div>}
        <button className="primary-button full-width" type="submit" disabled={busy}>
          {busy ? <Loader2 className="spin" size={17} /> : mode === "login" ? <LogIn size={17} /> : <UserPlus size={17} />}
          {mode === "login" ? "Login" : "Register"}
        </button>
      </form>
    </section>
  );
}

function DashboardView({ metrics, campaigns, companies, people, providerStatus, onOpenSearch, onRun, busy }) {
  const latest = campaigns[0];
  return (
    <div className="view-stack">
      <section className="dashboard-grid">
        <div className="panel search-hero">
          <div className="hero-copy">
            <span className="eyebrow">Lead workflow</span>
            <h2>Search a market, inspect company websites, enrich decision makers.</h2>
            <p>Example: find 10 construction companies in the US and return owner, founder, or CEO contacts.</p>
          </div>
          <button className="primary-button" onClick={onOpenSearch} type="button">
            <MessageSquareText size={17} />
            Start search
          </button>
        </div>
        <PipelineChart metrics={metrics} />
      </section>

      <section className="metric-grid">
        <MetricCard label="Campaigns" value={metrics.campaigns} icon={<Search size={18} />} />
        <MetricCard label="Companies" value={metrics.companies} icon={<Building2 size={18} />} />
        <MetricCard label="People" value={metrics.people} icon={<Users size={18} />} />
        <MetricCard label="Reachable sites" value={metrics.reachable} icon={<Globe2 size={18} />} />
      </section>

      <section className="split-grid">
        <div className="panel">
          <PanelHead title="Recent campaigns" subtitle={`${campaigns.length} searches`} />
          <CampaignList campaigns={campaigns.slice(0, 5)} providerReady={providerStatus?.ready} busy={busy} onRun={onRun} />
        </div>
        <div className="panel">
          <PanelHead title="Latest people" subtitle={`${people.length} enriched contacts`} />
          <PeopleList people={people.slice(0, 6)} companies={companies} compact />
        </div>
      </section>
    </div>
  );
}

function SearchView({ campaignForm, setCampaignForm, providerStatus, campaigns, busy, onCreate, onRun }) {
  function updateQuery(value) {
    setCampaignForm((current) => ({
      ...current,
      query: value,
      ...inferCampaignFields(value, current)
    }));
  }

  const briefItems = [
    ["Campaign", campaignForm.name],
    ["Industry", titleCase(campaignForm.industry)],
    ["Country", campaignForm.country],
    ["Companies", campaignForm.company_count],
    ["Roles", campaignForm.target_roles]
  ];

  return (
    <div className="search-grid">
      <section className="panel chat-panel">
        <div className="chat-stream">
          <ChatBubble tone="assistant" icon={<Bot size={17} />}>
            Describe the companies you want. I will turn your request into a campaign, verify each company website, and enrich the best available decision makers.
          </ChatBubble>
          <ChatBubble tone="user" icon={<MessageSquareText size={17} />}>
            {campaignForm.query}
          </ChatBubble>
          <ChatBubble tone="assistant" icon={<Sparkles size={17} />}>
            Search brief: {campaignForm.company_count} companies in {campaignForm.country}; target roles are {campaignForm.target_roles}.
          </ChatBubble>
        </div>

        <form className="chat-composer" onSubmit={onCreate}>
          <div className="prompt-suggestions" aria-label="Suggested searches">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                className={campaignForm.query === prompt ? "active" : ""}
                key={prompt}
                onClick={() => updateQuery(prompt)}
                type="button"
              >
                {prompt.replace(/^Find\s+/i, "")}
              </button>
            ))}
          </div>
          <textarea
            value={campaignForm.query}
            onChange={(event) => updateQuery(event.target.value)}
            placeholder="Find SaaS CEOs in US companies"
            required
          />
          <div className="brief-grid" aria-label="Search brief">
            {briefItems.map(([label, value]) => (
              <div className="brief-item" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <div className="composer-actions">
            <span className="composer-note">Websites are checked for redirects, block pages, logo, and confidence.</span>
            <button className="primary-button" type="submit" disabled={busy === "campaign"}>
              {busy === "campaign" ? <Loader2 className="spin" size={17} /> : <Send size={17} />}
              Create search
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <PanelHead title="Campaign queue" subtitle={`${campaigns.length} saved searches`} />
        <CampaignList campaigns={campaigns} providerReady={providerStatus?.ready} busy={busy} onRun={onRun} />
      </section>
    </div>
  );
}

function CompaniesView({ companies, campaigns }) {
  return (
    <section className="panel">
      <PanelHead title="Companies" subtitle={`${companies.length} discovered websites`} />
      <CompaniesTable companies={companies} campaigns={campaigns} />
    </section>
  );
}

function PeopleView({ people, companies, campaigns }) {
  return (
    <section className="panel">
      <PanelHead title="People" subtitle={`${people.length} enriched decision makers`} />
      <PeopleTable people={people} companies={companies} campaigns={campaigns} />
    </section>
  );
}

function ProcessView({ latestCampaign, companies, people }) {
  return (
    <div className="view-stack">
      <section className="panel process-panel">
        <PanelHead title="Execution path" subtitle={latestCampaign ? latestCampaign.name : "No campaign selected"} />
        <div className="process-steps">
          <ProcessStep icon={<Search size={18} />} title="Campaign" value={latestCampaign?.status || "draft"} detail={latestCampaign?.query || "Create a search request"} />
          <ProcessStep icon={<Globe2 size={18} />} title="Discovery" value={`${companies.length} companies`} detail="The search engine returns official company websites." />
          <ProcessStep icon={<Building2 size={18} />} title="Website signals" value={`${companies.filter((company) => company.website_reachable).length} reachable`} detail="Each site is checked for redirects, block pages, logo, and metadata." />
          <ProcessStep icon={<Users size={18} />} title="People" value={`${people.length} contacts`} detail="Decision makers are enriched from the verified company domain." />
        </div>
      </section>
      <section className="panel integration-panel">
        <PanelHead title="Quality checks" subtitle="How each company is verified" />
        <div className="integration-grid">
          <IntegrationCard name="Official website" ready detail="Company domains are checked before enrichment." />
          <IntegrationCard name="Redirect review" ready detail="External redirects and blocked pages are marked clearly." />
          <IntegrationCard name="Confidence score" ready detail="Company discovery and website verification show confidence." />
        </div>
      </section>
    </div>
  );
}

function PipelineChart({ metrics }) {
  const stages = [
    ["Searches", metrics.campaigns, Search],
    ["Companies", metrics.companies, Building2],
    ["Reachable", metrics.reachable, Globe2],
    ["People", metrics.people, Users]
  ];
  const max = Math.max(...stages.map(([, value]) => value), 1);

  return (
    <div className="panel chart-panel">
      <PanelHead title="Pipeline" subtitle="Latest funnel" />
      <div className="bar-chart">
        {stages.map(([label, value, Icon]) => (
          <div className="bar-row" key={label}>
            <span><Icon size={15} />{label}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.max(8, (value / max) * 100)}%` }} />
            </div>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PanelHead({ title, subtitle }) {
  return (
    <div className="panel-head">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

function ChatBubble({ tone, icon, children }) {
  return (
    <div className={`chat-bubble ${tone}`}>
      <div className="bubble-icon">{icon}</div>
      <p>{children}</p>
    </div>
  );
}

function CampaignList({ campaigns, providerReady, busy, onRun }) {
  if (!campaigns.length) return <EmptyState icon={<Search size={26} />} text="No searches yet" />;

  return (
    <div className="campaign-list">
      {campaigns.map((campaign) => (
        <article className="campaign-item" key={campaign.id}>
          <div>
            <strong>{campaign.name}</strong>
            <p>{campaign.query}</p>
            <div className="item-meta">
              <span>{campaign.country}</span>
              <span>{campaign.company_count} companies</span>
              <span>{asTime(campaign.created_at)}</span>
            </div>
          </div>
          <div className="item-actions">
            <span className={`status ${campaign.status}`}>{statusIcon(campaign.status)}{statusLabel(campaign.status)}</span>
            <button className="small-button" onClick={() => onRun(campaign.id)} disabled={!providerReady || busy === `run-${campaign.id}` || campaign.status === "running"} type="button">
              {busy === `run-${campaign.id}` ? <Loader2 className="spin" size={15} /> : <Play size={15} />}
              Run
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}

function CompaniesTable({ companies, campaigns }) {
  if (!companies.length) return <EmptyState icon={<Building2 size={26} />} text="No companies discovered yet" />;
  const campaignById = new Map(campaigns.map((campaign) => [campaign.id, campaign.name]));

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Website</th>
            <th>Search</th>
            <th>Verification</th>
            <th>Confidence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company) => (
            <tr key={company.id}>
              <td>
                <div className="company-cell">
                  <CompanyLogo company={company} />
                  <div>
                    <strong>{company.name}</strong>
                    <p className="muted-line">{company.industry || "Industry unknown"} - {company.country || "Country unknown"}</p>
                  </div>
                </div>
              </td>
              <td>
                {company.website_url ? (
                  <a className="external-link" href={company.website_url} target="_blank" rel="noreferrer">
                    {company.domain || company.website_url} <ExternalLink size={13} />
                  </a>
                ) : (
                  "No website"
                )}
                {company.website_title && <p className="muted-line">{company.website_title}</p>}
              </td>
              <td>{campaignById.get(company.campaign_id) || shortId(company.campaign_id)}</td>
              <td>
                <div className="stacked-text">
                  <span className={`verification ${company.website_verification_status || "not_verified"}`}>
                    {verificationLabel(company)}
                  </span>
                  <span>{verificationDetail(company)}</span>
                </div>
              </td>
              <td>
                <ConfidenceMeter value={company.website_confidence || company.confidence || 0} />
                <p className="muted-line">Discovery {company.confidence || 0}%</p>
              </td>
              <td><span className={`status ${company.status}`}>{statusIcon(company.status)}{statusLabel(company.status)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PeopleTable({ people, companies, campaigns }) {
  if (!people.length) return <EmptyState icon={<Users size={26} />} text="No people enriched yet" />;
  const companyById = new Map(companies.map((company) => [company.id, company.name]));
  const campaignById = new Map(campaigns.map((campaign) => [campaign.id, campaign.name]));

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Person</th>
            <th>Title</th>
            <th>Company</th>
            <th>Contact</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {people.map((person) => (
            <tr key={person.id}>
              <td>
                <strong>{person.full_name}</strong>
                {person.linkedin_url && (
                  <a className="external-link" href={person.linkedin_url} target="_blank" rel="noreferrer">
                    LinkedIn <ExternalLink size={13} />
                  </a>
                )}
              </td>
              <td>{person.title || person.role || "Decision maker"}</td>
              <td>
                {companyById.get(person.company_id) || campaignById.get(person.campaign_id) || shortId(person.company_id)}
              </td>
              <td>
                <div className="stacked-text">
                  <span>{person.email || "No email"}</span>
                  <span>{person.phone || "No phone"}</span>
                </div>
              </td>
              <td>
                <ConfidenceMeter value={person.confidence || 0} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PeopleList({ people, companies, compact }) {
  if (!people.length) return <EmptyState icon={<Users size={24} />} text="No people yet" compact={compact} />;
  const companyById = new Map(companies.map((company) => [company.id, company.name]));
  return (
    <div className="people-list">
      {people.map((person) => (
        <article className="person-card" key={person.id}>
          <div className="avatar">{person.full_name?.slice(0, 1) || "P"}</div>
          <div>
            <strong>{person.full_name}</strong>
            <p>{person.title || person.role || "Decision maker"}</p>
            <span>{companyById.get(person.company_id) || "Company"}</span>
          </div>
          {person.linkedin_url && (
            <a href={person.linkedin_url} target="_blank" rel="noreferrer" title="Open LinkedIn">
              <ExternalLink size={15} />
            </a>
          )}
        </article>
      ))}
    </div>
  );
}

function CompanyLogo({ company }) {
  const logo = company.company_logo_url || company.website_signals?.logo_url;
  if (logo) {
    return (
      <img
        className="company-logo"
        src={logo}
        alt=""
        onError={(event) => {
          event.currentTarget.replaceWith(Object.assign(document.createElement("div"), {
            className: "company-logo fallback",
            textContent: company.name?.slice(0, 1) || "C"
          }));
        }}
      />
    );
  }
  return <div className="company-logo fallback">{company.name?.slice(0, 1) || "C"}</div>;
}

function ConfidenceMeter({ value }) {
  const score = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="confidence-meter" aria-label={`Confidence ${score}%`}>
      <div className="confidence-track">
        <span style={{ width: `${score}%` }} />
      </div>
      <strong>{score}%</strong>
    </div>
  );
}

function verificationLabel(company) {
  const status = company.website_verification_status || company.website_signals?.verification_status;
  if (status === "verified") return "Verified website";
  if (status === "redirected") return "Redirected";
  if (status === "blocked") return "Blocked";
  if (status === "unreachable") return "Unreachable";
  return company.website_reachable ? "Reachable" : "Not verified";
}

function verificationDetail(company) {
  const reason = company.website_signals?.verification_reason;
  if (reason) return reason;
  const finalUrl = company.website_final_url || company.website_signals?.final_url;
  if (finalUrl && finalUrl !== company.website_url) return `Final URL: ${finalUrl}`;
  return company.website_signals?.keywords?.slice(0, 3).join(", ") || "No website issue reported";
}

function ProcessStep({ icon, title, value, detail }) {
  return (
    <article className="process-step">
      <div className="process-icon">{icon}</div>
      <div>
        <span>{title}</span>
        <strong>{value}</strong>
        <p>{detail}</p>
      </div>
      <ArrowRight size={16} />
    </article>
  );
}

function IntegrationCard({ name, ready, detail }) {
  return (
    <article className={`integration-card ${ready ? "ready" : "blocked"}`}>
      <div>
        {ready ? <CheckCircle2 size={17} /> : <AlertCircle size={17} />}
        <strong>{name}</strong>
      </div>
      <p>{detail}</p>
    </article>
  );
}

function EmptyState({ icon, text, compact = false }) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      {icon}
      <span>{text}</span>
    </div>
  );
}

function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast ${toast.kind}`}>
          <div className="toast-icon">
            {toast.kind === "success" ? <CheckCircle2 size={18} /> : toast.kind === "error" ? <AlertCircle size={18} /> : <Clock3 size={18} />}
          </div>
          <div>
            <strong>{toast.title}</strong>
            {toast.body && <p>{toast.body}</p>}
          </div>
          <button onClick={() => onDismiss(toast.id)} title="Dismiss" type="button">
            <X size={15} />
          </button>
        </div>
      ))}
    </div>
  );
}
