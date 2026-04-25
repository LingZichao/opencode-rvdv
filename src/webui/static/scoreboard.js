(function () {
  const FLOAT_COLUMNS = new Set(["baseline_line_pct", "current_line_pct", "last_improved_delta_pct"]);
  const ROW_HEIGHT = 42;
  const BUFFER_ROWS = 18;
  const INITIAL_WINDOW = 200;

  const state = {
    snapshotVersion: "",
    columns: [],
    filterOptions: {},
    query: {
      search: "",
      kind: "",
      vp_group: "",
      status: "",
      running_state: "",
      sort_by: "",
      sort_dir: "asc",
    },
    totalRows: 0,
    windowOffset: 0,
    windowRows: [],
    requestedWindowKey: "",
    eventSource: null,
    tableFetchToken: 0,
  };

  const elements = {
    connectionBadge: document.getElementById("connection-badge"),
    snapshotVersion: document.getElementById("snapshot-version"),
    overallCoverageValue: document.getElementById("overall-coverage-value"),
    activeKind: document.getElementById("active-kind"),
    activeKindCoverage: document.getElementById("active-kind-coverage"),
    summaryGrid: document.getElementById("summary-grid"),
    scoreboardRoot: document.getElementById("scoreboard-root"),
    lastRefresh: document.getElementById("last-refresh"),
    chartLatest: document.getElementById("chart-latest"),
    chartLegend: document.getElementById("chart-legend"),
    chart: document.getElementById("coverage-chart"),
    filteredCount: document.getElementById("filtered-count"),
    searchInput: document.getElementById("search-input"),
    kindFilter: document.getElementById("kind-filter"),
    vpGroupFilter: document.getElementById("vp-group-filter"),
    statusFilter: document.getElementById("status-filter"),
    runningStateFilter: document.getElementById("running-state-filter"),
    tableShell: document.getElementById("table-shell"),
    tableHead: document.getElementById("table-head"),
    tableBody: document.getElementById("table-body"),
  };

  const summaryTiles = [
    { key: "total_vps", label: "Total VPs", formatter: formatInteger },
    { key: "executable_vps", label: "Executable VPs", formatter: formatInteger },
    { key: "blocked_vps", label: "Blocked VPs", formatter: formatInteger },
    { key: "pending_vps", label: "Pending VPs", formatter: formatInteger },
    { key: "done_covered_vps", label: "Done Covered VPs", formatter: formatInteger },
    { key: "inflight_vps", label: "Inflight VPs", formatter: formatInteger },
    { key: "parallelism", label: "Parallelism", formatter: formatInteger },
    { key: "last_merge_version", label: "Last Merge Version", formatter: formatInteger },
  ];

  function setConnectionState(mode, text) {
    elements.connectionBadge.textContent = text;
    elements.connectionBadge.className = `connection-badge ${mode}`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function slugify(value) {
    return String(value).replace(/[^a-zA-Z0-9_-]+/g, "_");
  }

  function formatInteger(value) {
    return new Intl.NumberFormat("en-US").format(Number(value || 0));
  }

  function formatPercent(value) {
    return `${Number(value || 0).toFixed(2)}%`;
  }

  function formatMaybe(value) {
    return value === null || value === undefined || value === "" ? "-" : String(value);
  }

  function debounce(fn, delay) {
    let timer = null;
    return function debounced(...args) {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => fn.apply(this, args), delay);
    };
  }

  async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      const message = await response.text();
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  function populateSelect(selectElement, values) {
    const currentValue = selectElement.value;
    const options = [`<option value="">All</option>`].concat(
      values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    );
    selectElement.innerHTML = options.join("");
    if (values.includes(currentValue)) {
      selectElement.value = currentValue;
    }
  }

  function renderSummary(summary) {
    elements.snapshotVersion.textContent = `snapshot ${summary.last_merge_version} / ${state.snapshotVersion}`;
    elements.overallCoverageValue.textContent = formatPercent(summary.overall_executable_pct);
    elements.activeKind.textContent = summary.active_kind || "-";
    elements.activeKindCoverage.textContent = formatPercent(summary.active_kind_executable_pct);
    elements.scoreboardRoot.textContent = formatMaybe(summary.scoreboard_root);
    elements.lastRefresh.textContent = formatMaybe(summary.last_refresh_at);

    elements.summaryGrid.innerHTML = summaryTiles
      .map(
        (tile) => `
          <article class="summary-tile">
            <span class="summary-label">${escapeHtml(tile.label)}</span>
            <strong>${escapeHtml(tile.formatter(summary[tile.key]))}</strong>
          </article>
        `
      )
      .join("");
  }

  function renderChart(points) {
    const width = 880;
    const height = 320;
    const chartMinPct = 75;
    const chartMaxPct = 100;
    const padding = { top: 24, right: 26, bottom: 34, left: 44 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const safePoints = points.length ? points : [{ merge_version: 0, overall_executable_pct: 0, timestamp: "" }];
    const xStep = safePoints.length === 1 ? 0 : chartWidth / (safePoints.length - 1);
    const y = (pct) =>
      padding.top +
      chartHeight -
      ((Math.max(chartMinPct, Math.min(chartMaxPct, pct)) - chartMinPct) / (chartMaxPct - chartMinPct)) * chartHeight;
    const x = (index) => padding.left + index * xStep;

    const polyline = safePoints
      .map((point, index) => `${x(index)},${y(Number(point.overall_executable_pct || 0))}`)
      .join(" ");

    const gridLines = [75, 80, 85, 90, 95, 100]
      .map((value) => {
        const yValue = y(value);
        return `
          <g>
            <line x1="${padding.left}" y1="${yValue}" x2="${width - padding.right}" y2="${yValue}" stroke="rgba(21,37,31,0.10)" stroke-dasharray="4 6"></line>
            <text x="10" y="${yValue + 4}" fill="rgba(93,116,106,0.85)" font-size="11">${value}%</text>
          </g>
        `;
      })
      .join("");

    const circles = safePoints
      .map((point, index) => {
        const xValue = x(index);
        const yValue = y(Number(point.overall_executable_pct || 0));
        return `
          <circle cx="${xValue}" cy="${yValue}" r="4.5" fill="#0f766e" stroke="rgba(255,255,255,0.9)" stroke-width="3"></circle>
        `;
      })
      .join("");

    const labels = safePoints
      .map((point, index) => {
        const xValue = x(index);
        return `
          <text x="${xValue}" y="${height - 10}" fill="rgba(93,116,106,0.85)" font-size="11" text-anchor="middle">
            v${escapeHtml(point.merge_version)}
          </text>
        `;
      })
      .join("");

    elements.chart.innerHTML = `
      <defs>
        <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="rgba(15, 118, 110, 0.28)"></stop>
          <stop offset="100%" stop-color="rgba(15, 118, 110, 0.04)"></stop>
        </linearGradient>
      </defs>
      ${gridLines}
      <path d="M ${polyline} L ${x(safePoints.length - 1)},${height - padding.bottom} L ${padding.left},${height - padding.bottom} Z" fill="url(#areaFill)"></path>
      <polyline fill="none" stroke="#0f766e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="${polyline}"></polyline>
      ${circles}
      ${labels}
    `;

    const latestPoint = safePoints[safePoints.length - 1];
    elements.chartLatest.textContent = formatPercent(latestPoint.overall_executable_pct);
    elements.chartLegend.innerHTML = safePoints
      .slice(Math.max(0, safePoints.length - 3))
      .map(
        (point) =>
          `<span>v${escapeHtml(point.merge_version)} · ${escapeHtml(formatPercent(point.overall_executable_pct))}</span>`
      )
      .join("");
  }

  function renderTableHead() {
    const headerHtml = state.columns
      .map((column) => {
        const isSorted = state.query.sort_by === column.key;
        const indicator = isSorted ? (state.query.sort_dir === "desc" ? "▼" : "▲") : "↕";
        return `
          <th>
            <button class="sort-button" data-column="${escapeHtml(column.key)}" type="button">
              <span>${escapeHtml(column.label)}</span>
              <span class="sort-indicator">${indicator}</span>
            </button>
          </th>
        `;
      })
      .join("");
    elements.tableHead.innerHTML = `<tr>${headerHtml}</tr>`;
    elements.tableHead.querySelectorAll(".sort-button").forEach((button) => {
      button.addEventListener("click", () => {
        const column = button.getAttribute("data-column") || "";
        if (state.query.sort_by === column) {
          state.query.sort_dir = state.query.sort_dir === "asc" ? "desc" : "asc";
        } else {
          state.query.sort_by = column;
          state.query.sort_dir = "asc";
        }
        state.requestedWindowKey = "";
        renderTableHead();
        resetScrollAndReload();
      });
    });
  }

  function formatCell(columnKey, value) {
    if (FLOAT_COLUMNS.has(columnKey)) {
      return formatPercent(value);
    }
    return formatMaybe(value);
  }

  function renderRows() {
    const topSpacerHeight = state.windowOffset * ROW_HEIGHT;
    const bottomSpacerHeight = Math.max(state.totalRows - state.windowOffset - state.windowRows.length, 0) * ROW_HEIGHT;
    const colSpan = state.columns.length || 1;

    if (!state.windowRows.length) {
      elements.tableBody.innerHTML = `
        <tr class="empty-state">
          <td colspan="${colSpan}">No rows matched the current filters.</td>
        </tr>
      `;
      return;
    }

    const bodyParts = [];
    if (topSpacerHeight > 0) {
      bodyParts.push(
        `<tr class="spacer-row"><td colspan="${colSpan}" style="height:${topSpacerHeight}px"></td></tr>`
      );
    }

    for (const row of state.windowRows) {
      const cells = state.columns
        .map((column) => {
          const rawValue = row[column.key];
          if (column.badge && rawValue) {
            const badgeClass = `badge badge-${column.key}-${slugify(rawValue)}`;
            return `<td title="${escapeHtml(rawValue)}"><span class="${badgeClass}">${escapeHtml(rawValue)}</span></td>`;
          }
          const className = column.numeric ? "numeric" : "";
          const text = formatCell(column.key, rawValue);
          return `<td class="${className}" title="${escapeHtml(text)}">${escapeHtml(text)}</td>`;
        })
        .join("");
      bodyParts.push(`<tr class="data-row">${cells}</tr>`);
    }

    if (bottomSpacerHeight > 0) {
      bodyParts.push(
        `<tr class="spacer-row"><td colspan="${colSpan}" style="height:${bottomSpacerHeight}px"></td></tr>`
      );
    }

    elements.tableBody.innerHTML = bodyParts.join("");
  }

  function visibleWindow() {
    const viewportRows = Math.max(Math.ceil(elements.tableShell.clientHeight / ROW_HEIGHT), 1);
    const start = Math.max(Math.floor(elements.tableShell.scrollTop / ROW_HEIGHT) - BUFFER_ROWS, 0);
    const limit = Math.max(viewportRows + BUFFER_ROWS * 2, INITIAL_WINDOW);
    return { start, limit };
  }

  async function loadTableWindow() {
    const { start, limit } = visibleWindow();
    const query = new URLSearchParams({
      offset: String(start),
      limit: String(limit),
      search: state.query.search,
      kind: state.query.kind,
      vp_group: state.query.vp_group,
      status: state.query.status,
      running_state: state.query.running_state,
      sort_by: state.query.sort_by,
      sort_dir: state.query.sort_dir,
    });

    const requestKey = query.toString();
    if (requestKey === state.requestedWindowKey) {
      return;
    }

    state.requestedWindowKey = requestKey;
    const token = ++state.tableFetchToken;
    const payload = await fetchJson(`/scoreboard/api/table?${query.toString()}`);
    if (token !== state.tableFetchToken) {
      return;
    }

    state.snapshotVersion = payload.snapshot_version;
    state.totalRows = payload.total;
    state.windowOffset = payload.offset;
    state.windowRows = payload.rows;
    elements.filteredCount.textContent = formatInteger(payload.total);
    renderRows();
  }

  function resetScrollAndReload() {
    elements.tableShell.scrollTop = 0;
    state.requestedWindowKey = "";
    void loadTableWindow();
  }

  function syncControls() {
    populateSelect(elements.kindFilter, state.filterOptions.kind || []);
    populateSelect(elements.vpGroupFilter, state.filterOptions.vp_group || []);
    populateSelect(elements.statusFilter, state.filterOptions.status || []);
    populateSelect(elements.runningStateFilter, state.filterOptions.running_state || []);
  }

  async function loadBootstrap() {
    const payload = await fetchJson("/scoreboard/api/bootstrap");
    state.snapshotVersion = payload.snapshot_version;
    state.columns = payload.columns;
    state.filterOptions = payload.filter_options;
    state.totalRows = payload.table.total;
    state.windowOffset = payload.table.offset;
    state.windowRows = payload.table.rows;

    syncControls();
    renderSummary(payload.summary);
    renderChart(payload.chart_points);
    renderTableHead();
    elements.filteredCount.textContent = formatInteger(payload.table.total);
    renderRows();
  }

  function bindControls() {
    elements.searchInput.addEventListener(
      "input",
      debounce((event) => {
        state.query.search = event.target.value.trim();
        state.requestedWindowKey = "";
        resetScrollAndReload();
      }, 180)
    );

    elements.kindFilter.addEventListener("change", (event) => {
      state.query.kind = event.target.value;
      state.requestedWindowKey = "";
      resetScrollAndReload();
    });

    elements.vpGroupFilter.addEventListener("change", (event) => {
      state.query.vp_group = event.target.value;
      state.requestedWindowKey = "";
      resetScrollAndReload();
    });

    elements.statusFilter.addEventListener("change", (event) => {
      state.query.status = event.target.value;
      state.requestedWindowKey = "";
      resetScrollAndReload();
    });

    elements.runningStateFilter.addEventListener("change", (event) => {
      state.query.running_state = event.target.value;
      state.requestedWindowKey = "";
      resetScrollAndReload();
    });

    elements.tableShell.addEventListener(
      "scroll",
      debounce(() => {
        void loadTableWindow();
      }, 20)
    );

    window.addEventListener(
      "resize",
      debounce(() => {
        state.requestedWindowKey = "";
        void loadTableWindow();
      }, 50)
    );
  }

  function connectStream() {
    if (state.eventSource) {
      state.eventSource.close();
    }

    const eventSource = new EventSource("/scoreboard/api/stream");
    state.eventSource = eventSource;
    setConnectionState("connection-connecting", "Connecting");

    eventSource.addEventListener("open", () => {
      setConnectionState("connection-live", "Live");
    });

    eventSource.addEventListener("snapshot", (event) => {
      try {
        const payload = JSON.parse(event.data);
        state.snapshotVersion = payload.snapshot_version;
        renderSummary(payload.summary);
        renderChart(payload.chart_points);
        state.requestedWindowKey = "";
        void loadTableWindow();
      } catch (error) {
        console.error("Failed to parse snapshot event", error);
      }
    });

    eventSource.onerror = () => {
      setConnectionState("connection-offline", "Reconnecting");
    };
  }

  async function init() {
    try {
      setConnectionState("connection-connecting", "Loading");
      bindControls();
      await loadBootstrap();
      connectStream();
      setConnectionState("connection-live", "Live");
    } catch (error) {
      setConnectionState("connection-offline", "Unavailable");
      console.error(error);
      elements.tableBody.innerHTML = `
        <tr class="empty-state">
          <td colspan="1">Unable to load scoreboard UI: ${escapeHtml(error.message || String(error))}</td>
        </tr>
      `;
    }
  }

  void init();
})();
