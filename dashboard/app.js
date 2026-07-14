const documentablePages = new Set(["overview", "insights", "knowledge", "proposals", "briefs", "operations"]);
const requestedPage = new URLSearchParams(window.location.search).get("view");

const state = {
  page: documentablePages.has(requestedPage) ? requestedPage : "overview",
  data: {},
};

const endpoints = {
  status: "/api/runtime/status",
  briefs: "/api/briefs",
  insights: "/api/insights",
  entities: "/api/entities",
  events: "/api/events",
  decisions: "/api/decisions",
  proposals: "/api/proposals",
  runs: "/api/runtime/runs",
};

document.querySelectorAll("nav button").forEach((button) => {
  button.classList.toggle("active", button.dataset.page === state.page);
  button.addEventListener("click", () => {
    state.page = button.dataset.page;
    document.querySelectorAll("nav button").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
});

async function load() {
  try {
    const health = await fetchJson("/health");
    document.querySelector("#health").textContent = health.status === "ok" ? "Healthy" : "Degraded";
    const entries = await Promise.all(Object.entries(endpoints).map(async ([key, url]) => [key, await fetchJson(url)]));
    state.data = Object.fromEntries(entries);
    render();
  } catch (error) {
    document.querySelector("#app").innerHTML = `<section class="state">Dashboard error: ${escapeHtml(error.message)}</section>`;
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${text}`);
  }
  return response.json();
}

function render() {
  const view = {
    overview,
    insights,
    knowledge,
    proposals,
    briefs,
    operations,
  }[state.page];
  document.querySelector("#app").innerHTML = view ? view() : `<section class="state">Unknown page.</section>`;
  bindProposalActions();
}

function overview() {
  const status = state.data.status || {};
  return `
    <section class="grid">
      ${metric("Insights", status.insights)}
      ${metric("Proposals", status.proposals)}
      ${metric("Entities", status.entities)}
      ${metric("Events", status.events)}
    </section>
    <section class="grid">
      ${card("Today's important insights", list((state.data.insights || []).slice(-5).reverse(), item => `<strong>${escapeHtml(item.claim)}</strong><p>${escapeHtml(item.why_it_matters)}</p><span class="badge">${item.confidence}</span>`))}
      ${card("Top decisions", list((state.data.decisions || []).slice(-6).reverse(), item => `<strong>${escapeHtml(item.action)}</strong><p>${escapeHtml(item.rationale)}</p>`))}
      ${card("Latest brief", latestBrief())}
      ${card("Recent events", list((state.data.events || []).slice(-5).reverse(), item => `<strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.summary)}</p>`))}
      ${card("Proposal statistics", proposalStats(status.proposal_metrics))}
      ${card("Runtime", `<p>DB: ${escapeHtml(status.db_path || "")}</p><p>Obsidian notes: ${status.obsidian?.note_count ?? 0}; broken links: ${status.obsidian?.broken_link_count ?? 0}</p>`)}
    </section>`;
}

function insights() {
  return `<section class="list">${list(state.data.insights || [], item => `
    <h3>${escapeHtml(item.claim)}</h3>
    <p>${escapeHtml(item.why_it_matters)}</p>
    <p><span class="badge">${item.confidence}</span> <span class="muted">${escapeHtml(item.generated_at)}</span></p>
    <p><strong>Evidence:</strong> ${escapeHtml((item.evidence_refs || []).join(", "))}</p>
    <p><strong>Related:</strong> ${escapeHtml([...(item.related_entity_refs || []), ...(item.related_event_refs || [])].join(", "))}</p>
    <p><strong>Possible action:</strong> ${escapeHtml((item.possible_actions || []).join(", ") || "Watch")}</p>
    <pre>${escapeHtml(JSON.stringify(item.provenance || {}, null, 2))}</pre>
  `)}</section>`;
}

function knowledge() {
  return `<section class="grid">
    ${card("Entities", list(state.data.entities || [], item => `<strong>${escapeHtml(item.canonical_name)}</strong><p>${escapeHtml(item.kind)} · ${escapeHtml(item.summary || "No summary")}</p>`))}
    ${card("Relationships and timeline", list([...(state.data.events || []), ...(state.data.decisions || [])], item => `<strong>${escapeHtml(item.title || item.action)}</strong><p>${escapeHtml(item.summary || item.rationale || "")}</p>`))}
  </section>`;
}

function proposals() {
  const proposals = state.data.proposals || [];
  return `<section class="list">${list(proposals, item => `
    <h3>${escapeHtml(item.proposal_type)} <span class="badge ${item.validation_status}">${item.validation_status}</span></h3>
    <p><strong>ID:</strong> ${escapeHtml(item.id)}</p>
    <p><strong>Evidence:</strong> ${escapeHtml((item.evidence_refs || []).join(", ") || "none")}</p>
    <p><strong>Provenance:</strong> ${escapeHtml(item.proposed_by)} · ${escapeHtml(item.model_name)}</p>
    <p><strong>Reasons:</strong> ${escapeHtml((item.rejection_reasons || []).join("; ") || "none")}</p>
    <pre>${escapeHtml(JSON.stringify(item.payload, null, 2))}</pre>
    <div class="actions">
      <button data-proposal-action="revalidate" data-proposal-id="${item.id}">Revalidate</button>
      <button data-proposal-action="accept" data-proposal-id="${item.id}">Accept</button>
      <input placeholder="Reject reason" data-reason-for="${item.id}" />
      <button data-proposal-action="reject" data-proposal-id="${item.id}">Reject</button>
    </div>
  `)}</section>`;
}

function briefs() {
  return `<section class="list">${list(state.data.briefs || [], item => `
    <h3>${escapeHtml(item.title)}</h3>
    <p><span class="badge">${escapeHtml(item.brief_type)}</span> ${escapeHtml(item.period_start)} → ${escapeHtml(item.period_end)}</p>
    <pre>${escapeHtml(item.markdown || item.executive_summary)}</pre>
  `)}</section>`;
}

function operations() {
  const status = state.data.status || {};
  return `<section class="grid">
    ${card("Runtime runs", list(state.data.runs || [], item => `<strong>${escapeHtml(item.stage)}</strong><p>${escapeHtml(item.status)} · ${escapeHtml(item.run_date)}</p>`))}
    ${card("Collector status", `<p>Configured mode degrades when live collectors or delivery credentials are missing.</p><p>Go-live ready: ${status.go_live_ready ? "yes" : "no"}</p>`)}
    ${card("Proposal metrics", proposalStats(status.proposal_metrics))}
    ${card("Delivery status", list(status.latest_briefs || [], item => `<strong>${escapeHtml(item.brief_type)}</strong><p>Notion=${escapeHtml(item.notion_status)} Telegram=${escapeHtml(item.telegram_status)}</p>`))}
    ${card("Readiness warnings", status.go_live_ready ? "<p>No credential gaps reported.</p>" : "<p>Live delivery credentials are optional for demo mode.</p>")}
    ${card("Obsidian export", `<p>Vault: ${escapeHtml(status.obsidian?.vault_path || "")}</p><p>Notes=${status.obsidian?.note_count ?? 0}; stale=${status.obsidian?.stale_count ?? 0}; broken=${status.obsidian?.broken_link_count ?? 0}</p>`)}
  </section>`;
}

function metric(label, value) {
  return `<section class="card"><div class="metric">${value ?? 0}</div><div class="muted">${label}</div></section>`;
}

function card(title, body) {
  return `<section class="card"><h2>${escapeHtml(title)}</h2>${body || empty()}</section>`;
}

function list(items, renderer) {
  if (!items || items.length === 0) return empty();
  return items.map((item) => `<div class="item">${renderer(item)}</div>`).join("");
}

function empty() {
  return `<p class="muted">No data yet. Run the demo seed to populate this view.</p>`;
}

function latestBrief() {
  const brief = [...(state.data.briefs || [])].pop();
  if (!brief) return empty();
  return `<h3>${escapeHtml(brief.title)}</h3><p>${escapeHtml(brief.executive_summary)}</p>`;
}

function proposalStats(metrics) {
  if (!metrics) return empty();
  return `<p>created=${metrics.proposals_created}, accepted=${metrics.proposals_accepted}, rejected=${metrics.proposals_rejected}, needs_review=${metrics.proposals_needing_review}</p><p>canonical_created=${metrics.canonical_records_created}, canonical_updated=${metrics.canonical_records_updated}, insights=${metrics.insight_count}</p>`;
}

function bindProposalActions() {
  document.querySelectorAll("[data-proposal-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.dataset.proposalId;
      const action = button.dataset.proposalAction;
      const options = { method: "POST", headers: { "Content-Type": "application/json" } };
      if (action === "reject") {
        const reason = document.querySelector(`[data-reason-for="${id}"]`)?.value || "Rejected from dashboard";
        options.body = JSON.stringify({ reason });
      }
      await fetchJson(`/api/proposals/${id}/${action}`, options);
      await load();
      state.page = "proposals";
      render();
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

load();
