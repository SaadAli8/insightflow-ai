import {
  Activity,
  AlertCircle,
  Bell,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileText,
  Globe2,
  Loader2,
  LogIn,
  LogOut,
  RefreshCw,
  Search,
  Send,
  Server,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Users,
  UserPlus,
  X
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";
const POLL_INTERVAL_MS = 8000;
const NOTIFICATION_LIMIT = 10;
const MAX_TOASTS = 4;
const ACTIVE_STATUSES = new Set(["queued", "processing", "extracting", "analyzing"]);
const DONE_STATUSES = new Set(["completed", "failed"]);

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
  if (status === "completed") return <CheckCircle2 size={15} />;
  if (status === "failed") return <AlertCircle size={15} />;
  if (ACTIVE_STATUSES.has(status)) return <Loader2 size={15} className="spin" />;
  return <Clock3 size={15} />;
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("insightflow-ai-token") || "");
  const [mode, setMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    email: "user000@example.com",
    password: "password123"
  });
  const [websiteUrl, setWebsiteUrl] = useState("https://fastapi.tiangolo.com");
  const [file, setFile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [users, setUsers] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [selectedResult, setSelectedResult] = useState(null);
  const [resultBusy, setResultBusy] = useState(false);
  const previousJobsRef = useRef(new Map());
  const notificationsLoadedRef = useRef(false);
  const knownNotificationIdsRef = useRef(new Set());

  const isAuthed = Boolean(token);

  const addToast = useCallback((toast) => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current.slice(-(MAX_TOASTS - 1)), { id, kind: "info", ...toast }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, 5200);
  }, []);

  const request = useCallback(
    async (path, options = {}) => {
      const headers = new Headers(options.headers || {});
      if (token) headers.set("Authorization", `Bearer ${token}`);
      if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }

      const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json") ? await response.json() : await response.text();

      if (!response.ok) {
        const detail =
          response.status === 429
            ? "Gateway rate limit reached. Please wait a moment and try again."
            : typeof data === "object"
              ? data.detail || data.message || JSON.stringify(data)
              : data;
        throw new Error(detail || `Request failed with ${response.status}`);
      }
      return data;
    },
    [token]
  );

  const loadJobs = useCallback(
    async ({ silent = false } = {}) => {
      if (!token) return;
      if (!silent) setBusy("jobs");
      try {
        const data = await request("/jobs?limit=150&scope=all");
        const previous = previousJobsRef.current;

        data.forEach((job) => {
          const oldStatus = previous.get(job.id);
          if (oldStatus && oldStatus !== job.status && DONE_STATUSES.has(job.status)) {
            addToast({
              kind: job.status === "completed" ? "success" : "error",
              title: job.status === "completed" ? "Job complete" : "Job failed",
              body: `${job.type} ${shortId(job.id)} is ${job.status}.`
            });
          }
        });

        previousJobsRef.current = new Map(data.map((job) => [job.id, job.status]));
        setJobs(data);
        setError("");
      } catch (err) {
        setError(err.message);
      } finally {
        if (!silent) setBusy("");
      }
    },
    [addToast, request, token]
  );

  const loadNotifications = useCallback(
    async ({ silent = false } = {}) => {
      if (!token) return;
      try {
        const data = await request(`/notifications?limit=${NOTIFICATION_LIMIT}&scope=all`);
        if (notificationsLoadedRef.current) {
          const known = knownNotificationIdsRef.current;
          data
            .filter((item) => !known.has(item.id))
            .slice(0, 3)
            .forEach((item) =>
              addToast({ kind: "success", title: item.title, body: item.body || "Notification received." })
            );
        }
        notificationsLoadedRef.current = true;
        knownNotificationIdsRef.current = new Set(data.map((item) => item.id));
        setNotifications(data);
      } catch (err) {
        if (!silent) setError(err.message);
      }
    },
    [addToast, request, token]
  );

  const clearNotifications = useCallback(async () => {
    if (!token || busy === "notifications") return;
    setBusy("notifications");
    setError("");
    try {
      const result = await request("/notifications?scope=all", { method: "DELETE" });
      setNotifications([]);
      notificationsLoadedRef.current = true;
      knownNotificationIdsRef.current = new Set();
      addToast({
        kind: "success",
        title: "Notifications cleared",
        body: `${result.deleted} event${result.deleted === 1 ? "" : "s"} removed.`
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }, [addToast, busy, request, token]);

  const loadUsers = useCallback(
    async () => {
      if (!token) return;
      try {
        const data = await request("/users?limit=100");
        setUsers(data);
      } catch {
        setUsers([]);
      }
    },
    [request, token]
  );

  const refreshAll = useCallback(
    async ({ silent = false } = {}) => {
      await Promise.all([loadJobs({ silent }), loadNotifications({ silent }), loadUsers()]);
    },
    [loadJobs, loadNotifications, loadUsers]
  );

  useEffect(() => {
    if (!token) return;
    refreshAll();
    const tick = () => {
      if (document.visibilityState === "visible") {
        refreshAll({ silent: true });
      }
    };
    const timer = window.setInterval(tick, POLL_INTERVAL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") refreshAll({ silent: true });
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refreshAll, token]);

  const metrics = useMemo(() => {
    const active = jobs.filter((job) => ACTIVE_STATUSES.has(job.status)).length;
    const complete = jobs.filter((job) => job.status === "completed").length;
    const failed = jobs.filter((job) => job.status === "failed").length;
    return { total: jobs.length, users: users.length, active, complete, failed };
  }, [jobs, users]);

  async function handleAuth(event) {
    event.preventDefault();
    setBusy("auth");
    setError("");
    try {
      if (mode === "register") {
        await request("/auth/register", {
          method: "POST",
          body: JSON.stringify(authForm)
        });
        addToast({ kind: "success", title: "User created", body: authForm.email });
      }

      const data = await request("/auth/login", {
        method: "POST",
        body: JSON.stringify(authForm)
      });
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
    setJobs([]);
    setUsers([]);
    setNotifications([]);
    previousJobsRef.current = new Map();
    notificationsLoadedRef.current = false;
    knownNotificationIdsRef.current = new Set();
    addToast({ title: "Signed out", body: "Session cleared." });
  }

  async function submitWebsite(event) {
    event.preventDefault();
    setBusy("website");
    setError("");
    try {
      const job = await request("/websites", {
        method: "POST",
        body: JSON.stringify({ url: websiteUrl })
      });
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      previousJobsRef.current.set(job.id, job.status);
      addToast({ title: "Website queued", body: `${websiteUrl} is processing.` });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function uploadFile(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const selectedFile = file;
    if (!selectedFile) return;
    setBusy("file");
    setError("");
    try {
      const form = new FormData();
      form.append("upload", selectedFile);
      const job = await request("/files/upload", {
        method: "POST",
        body: form
      });
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      previousJobsRef.current.set(job.id, job.status);
      setFile(null);
      formElement.reset();
      addToast({ title: "File queued", body: `${selectedFile.name} is processing.` });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function openResult(job) {
    setResultBusy(true);
    setSelectedResult({ job, data: null, error: "" });
    try {
      const data = await request(`/jobs/${job.id}/result`);
      setSelectedResult({ job, data, error: "" });
    } catch (err) {
      setSelectedResult({ job, data: null, error: err.message });
    } finally {
      setResultBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Activity size={22} />
          </div>
          <div>
            <h1>InsightFlow AI Console</h1>
            <p>Kong + FastAPI + Celery</p>
          </div>
        </div>
        <div className="topbar-actions">
          <a href="http://localhost:5555" target="_blank" rel="noreferrer" title="Open Celery Flower">
            <Server size={16} />
            Flower
            <ExternalLink size={14} />
          </a>
          <a href="http://localhost:1337" target="_blank" rel="noreferrer" title="Open Konga">
            <ShieldCheck size={16} />
            Konga
            <ExternalLink size={14} />
          </a>
          {isAuthed && (
            <button className="ghost-button" onClick={logout} title="Sign out">
              <LogOut size={16} />
              Sign out
            </button>
          )}
        </div>
      </header>

      <main className={isAuthed ? "workspace" : "auth-workspace"}>
        {!isAuthed ? (
          <AuthPanel
            mode={mode}
            setMode={setMode}
            form={authForm}
            setForm={setAuthForm}
            busy={busy === "auth"}
            error={error}
            onSubmit={handleAuth}
          />
        ) : (
          <>
            <section className="status-strip" aria-label="Pipeline status">
              <Metric icon={<Users size={18} />} label="Users" value={metrics.users} />
              <Metric icon={<Activity size={18} />} label="Jobs" value={metrics.total} />
              <Metric icon={<Loader2 size={18} />} label="Processing" value={metrics.active} />
              <Metric icon={<CheckCircle2 size={18} />} label="Complete" value={metrics.complete} />
              <Metric icon={<AlertCircle size={18} />} label="Failed" value={metrics.failed} />
            </section>

            <section className="controls-grid">
              <form className="panel" onSubmit={submitWebsite}>
                <div className="panel-title">
                  <Globe2 size={18} />
                  <h2>Website</h2>
                </div>
                <div className="input-row">
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(event) => setWebsiteUrl(event.target.value)}
                    placeholder="https://example.com"
                    required
                  />
                  <button type="submit" disabled={busy === "website"} title="Submit website">
                    {busy === "website" ? <Loader2 className="spin" size={17} /> : <Send size={17} />}
                    Submit
                  </button>
                </div>
              </form>

              <form className="panel" onSubmit={uploadFile}>
                <div className="panel-title">
                  <FileText size={18} />
                  <h2>File</h2>
                </div>
                <div className="file-row">
                  <label className="file-input">
                    <UploadCloud size={18} />
                    <span>{file ? file.name : "Choose file"}</span>
                    <input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
                  </label>
                  <button type="submit" disabled={!file || busy === "file"} title="Upload file">
                    {busy === "file" ? <Loader2 className="spin" size={17} /> : <UploadCloud size={17} />}
                    Upload
                  </button>
                </div>
              </form>
            </section>

            {error && (
              <div className="error-banner" role="alert">
                <AlertCircle size={17} />
                {error}
              </div>
            )}

            <section className="data-layout">
              <div className="table-panel">
                <div className="section-head">
                  <div>
                    <h2>Jobs</h2>
                    <p>{metrics.active} active in the queue</p>
                  </div>
                  <button className="icon-button" onClick={() => refreshAll()} title="Refresh jobs">
                    <RefreshCw size={17} className={busy === "jobs" ? "spin" : ""} />
                  </button>
                </div>
                <JobsTable jobs={jobs} onOpenResult={openResult} />
              </div>

              <aside className="side-stack">
                <div className="users-panel">
                  <div className="section-head">
                    <div>
                      <h2>Users</h2>
                      <p>{users.length} seeded accounts</p>
                    </div>
                    <Users size={18} />
                  </div>
                  <UserList users={users} />
                </div>

                <div className="notifications-panel">
                  <div className="section-head">
                    <div>
                      <h2>Notifications</h2>
                      <p>{notifications.length ? `Latest ${notifications.length} events` : "No recent events"}</p>
                    </div>
                    <div className="section-actions">
                      <Bell size={18} />
                      <button
                        className="icon-button danger"
                        onClick={clearNotifications}
                        disabled={!notifications.length || busy === "notifications"}
                        title="Clear notifications"
                      >
                        {busy === "notifications" ? <Loader2 size={17} className="spin" /> : <Trash2 size={17} />}
                      </button>
                    </div>
                  </div>
                  <NotificationList notifications={notifications} />
                </div>
              </aside>
            </section>
          </>
        )}
      </main>

      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((items) => items.filter((item) => item.id !== id))} />

      {selectedResult && (
        <ResultDrawer
          result={selectedResult}
          busy={resultBusy}
          onClose={() => setSelectedResult(null)}
        />
      )}
    </div>
  );
}

function AuthPanel({ mode, setMode, form, setForm, busy, error, onSubmit }) {
  return (
    <section className="auth-panel">
      <div className="auth-copy">
        <div className="brand-mark large">
          <ShieldCheck size={32} />
        </div>
        <h2>InsightFlow AI Console</h2>
        <p>Local workflow console for website and file analysis jobs.</p>
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
          <input
            type="email"
            value={form.email}
            onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            minLength={6}
            required
          />
        </label>
        {error && (
          <div className="error-banner compact" role="alert">
            <AlertCircle size={17} />
            {error}
          </div>
        )}
        <button className="full-button" type="submit" disabled={busy}>
          {busy ? <Loader2 className="spin" size={17} /> : mode === "login" ? <LogIn size={17} /> : <UserPlus size={17} />}
          {mode === "login" ? "Login" : "Register"}
        </button>
      </form>
    </section>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function JobsTable({ jobs, onOpenResult }) {
  if (!jobs.length) {
    return (
      <div className="empty-state">
        <Search size={28} />
        <span>No jobs yet</span>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Job</th>
            <th>Type</th>
            <th>Status</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td className="mono">{shortId(job.id)}</td>
              <td>{job.type}</td>
              <td>
                <span className={`status ${job.status}`}>
                  {statusIcon(job.status)}
                  {statusLabel(job.status)}
                </span>
              </td>
              <td>{asTime(job.created_at)}</td>
              <td className="right">
                <button
                  className="small-button"
                  onClick={() => onOpenResult(job)}
                  disabled={job.status !== "completed"}
                  title="View result"
                >
                  <Search size={15} />
                  Result
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UserList({ users }) {
  if (!users.length) {
    return (
      <div className="empty-state users-empty">
        <Users size={24} />
        <span>No users visible</span>
      </div>
    );
  }

  return (
    <div className="user-list">
      {users.slice(0, 10).map((user) => (
        <div key={user.id} className="user-item">
          <div>
            <strong>{user.email}</strong>
            <p>{user.role}</p>
          </div>
          <time>{asTime(user.created_at)}</time>
        </div>
      ))}
    </div>
  );
}

function NotificationList({ notifications }) {
  if (!notifications.length) {
    return (
      <div className="empty-state compact-empty">
        <Bell size={24} />
        <span>No notifications</span>
      </div>
    );
  }

  return (
    <div className="notification-list">
      {notifications.slice(0, NOTIFICATION_LIMIT).map((item) => (
        <div key={item.id} className="notification-item">
          <div>
            <strong>{item.title}</strong>
            <p>{item.body}</p>
          </div>
          <time>{asTime(item.created_at)}</time>
        </div>
      ))}
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
          <button onClick={() => onDismiss(toast.id)} title="Dismiss">
            <X size={15} />
          </button>
        </div>
      ))}
    </div>
  );
}

function ResultDrawer({ result, busy, onClose }) {
  const payload = result.data?.result;

  return (
    <div className="drawer-backdrop" role="presentation">
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="Analysis result">
        <div className="drawer-head">
          <div>
            <span className="mono">{shortId(result.job.id)}</span>
            <h2>Analysis result</h2>
          </div>
          <button className="icon-button" onClick={onClose} title="Close result">
            <X size={18} />
          </button>
        </div>

        {busy ? (
          <div className="drawer-loading">
            <Loader2 className="spin" size={28} />
          </div>
        ) : result.error ? (
          <div className="error-banner">
            <AlertCircle size={17} />
            {result.error}
          </div>
        ) : (
          <div className="result-content">
            <section>
              <h3>Summary</h3>
              <p>{result.data.summary}</p>
            </section>
            {payload?.key_points?.length > 0 && (
              <section>
                <h3>Key points</h3>
                <ul>
                  {payload.key_points.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </section>
            )}
            {payload?.topics?.length > 0 && (
              <section>
                <h3>Topics</h3>
                <div className="tag-row">
                  {payload.topics.map((item) => (
                    <span key={item}>{item}</span>
                  ))}
                </div>
              </section>
            )}
            <section>
              <h3>Raw JSON</h3>
              <pre>{JSON.stringify(result.data.result, null, 2)}</pre>
            </section>
          </div>
        )}
      </aside>
    </div>
  );
}
