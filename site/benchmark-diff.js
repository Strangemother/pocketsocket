const { createApp, computed, ref } = Vue;

createApp({
    setup() {
        const diff = ref(null);
        const error = ref("");
        const activeSuite = ref("");
        const view = ref("objects");
        const isLight = ref(localStorage.getItem("pocketsocket-theme") === "light");
        const sortState = ref({});

        function applyTheme() {
            document.documentElement.classList.toggle("light-theme", isLight.value);
            localStorage.setItem("pocketsocket-theme", isLight.value ? "light" : "dark");
        }
        function toggleTheme() {
            isLight.value = !isLight.value;
            applyTheme();
        }
        function shortPath(path) {
            return path ? path.split("/").filter(Boolean).pop() : "unknown";
        }
        async function loadDiff() {
            error.value = "";
            try {
                const response = await fetch("diff.json", { cache: "no-store" });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                diff.value = await response.json();
                if (!activeSuite.value) activeSuite.value = Object.keys(diff.value.reports)[0] || "";
            } catch (reason) {
                error.value = `Could not load diff.json. Serve this folder over HTTP, then refresh. (${reason.message})`;
            }
        }
        function isNumericDiff(value) {
            return value && typeof value === "object" && "a" in value && "b" in value && "delta" in value && "percent_change" in value;
        }
        function flatten(value, path = [], rows = []) {
            if (!value || typeof value !== "object") return rows;
            for (const [key, child] of Object.entries(value)) {
                if (isNumericDiff(child)) rows.push({ path: [...path, key], value: child });
                else if (child && typeof child === "object" && !Array.isArray(child)) flatten(child, [...path, key], rows);
            }
            return rows;
        }
        function formatValue(value) {
            if (value === null || value === undefined) return "-";
            if (typeof value !== "number") return String(value);
            if (Number.isInteger(value)) return value.toLocaleString();
            return Math.abs(value) >= 100 ? value.toFixed(1) : value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
        }
        function formatPercent(value) {
            return value === null || value === undefined ? "n/a" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
        }
        function changeClass(value) {
            if (value === 0 || value === null || value === undefined) return "unchanged";
            return value > 0 ? "positive" : "negative";
        }
        function rankingColumn(columns) {
            return ["rate", "relative_to_fastest", "vs_rate", "vs_best"].find(column => columns.includes(column)) || "";
        }
        function columnLabel(column) {
            const labels = {
                "__label": "Server",
                rate: "Rate",
                relative_to_fastest: "Relative to fastest",
                vs_rate: "Compared with best rate",
                vs_best: "Compared with best"
            };
            return labels[column] || column.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
        }
        function columnDescription(column) {
            const descriptions = {
                "__label": "Contender or object",
                rate: "Messages per second",
                relative_to_fastest: "Lower multiplier is faster",
                vs_rate: "Higher share is better",
                vs_best: "Higher share is better"
            };
            return descriptions[column] || "Latest value";
        }
        function rankingDirection(column) {
            return column === "relative_to_fastest" ? "lower is better" : "higher is better";
        }
        function isConstantColumn(column, rows) {
            if (!rows.length || rows.some(row => !row.cells[column])) return false;
            const firstValue = rows[0].cells[column].b;
            return rows.every(row => row.cells[column].b === firstValue);
        }
        function compactTable(table) {
            const constantColumns = table.columns
                .filter(column => isConstantColumn(column, table.rows))
                .map(column => ({ column, value: table.rows[0].cells[column].b }));
            return {
                ...table,
                displayColumns: table.columns.filter(column => !constantColumns.some(item => item.column === column)),
                constantColumns
            };
        }
        function markTopPerformer(table) {
            const column = rankingColumn(table.columns);
            if (!column) return { ...table, rankingColumn: "", topLabel: "" };
            const rankedRows = table.rows.filter(row => Number.isFinite(row.cells[column]?.b));
            const topValue = rankedRows.reduce((best, row) => column === "relative_to_fastest" ? Math.min(best, row.cells[column].b) : Math.max(best, row.cells[column].b), column === "relative_to_fastest" ? Infinity : -Infinity);
            return {
                ...table,
                rankingColumn: column,
                topLabel: rankedRows.find(row => row.cells[column].b === topValue)?.label || ""
            };
        }
        function rowClasses(row, table) {
            const isPocketSocket = row.label.startsWith("ps-");
            const isTopPerformer = row.label === table.topLabel;
            return {
                "ps-row": isPocketSocket,
                "top-row": isTopPerformer,
                "ps-top-row": isPocketSocket && isTopPerformer
            };
        }
        function sortTable(tableName, column) {
            const current = sortState.value[tableName] || { column: column, direction: "asc" };
            const direction = current?.column === column && current.direction === "asc" ? "desc" : "asc";
            sortState.value = { ...sortState.value, [tableName]: { column, direction } };
        }
        function defaultSort(table) {
            if (!table.rankingColumn) return null;
            return {
                column: table.rankingColumn,
                direction: table.rankingColumn === "relative_to_fastest" ? "asc" : "desc"
            };
        }
        function sortRows(table) {
            const sort = sortState.value[table.name] || defaultSort(table);
            if (!sort) return table.rows;
            return [...table.rows].sort((left, right) => {
                const leftValue = sort.column === "__label" ? left.label : left.cells[sort.column]?.b;
                const rightValue = sort.column === "__label" ? right.label : right.cells[sort.column]?.b;
                if (leftValue === rightValue) return 0;
                if (leftValue === undefined || leftValue === null) return 1;
                if (rightValue === undefined || rightValue === null) return -1;
                const comparison = typeof leftValue === "number" && typeof rightValue === "number"
                    ? leftValue - rightValue
                    : String(leftValue).localeCompare(String(rightValue));
                return sort.direction === "asc" ? comparison : -comparison;
            });
        }
        function sortIndicator(tableName, column) {
            const table = pivotTables.value.find(item => item.name === tableName);
            const sort = sortState.value[tableName] || (table && defaultSort(table));
            if (!sort || sort.column !== column) return "";
            return sort.direction === "asc" ? " ^" : " v";
        }

        applyTheme();
        loadDiff();

        const suites = computed(() => diff.value ? Object.keys(diff.value.reports) : []);
        const activeReport = computed(() => diff.value?.reports?.[activeSuite.value]);
        const rows = computed(() => {
            if (!activeReport.value?.benchmark) return [];
            const grouped = new Map();
            for (const row of flatten(activeReport.value.benchmark)) {
                const groupName = row.path.slice(0, -1).join(" / ") || "Benchmark";
                if (!grouped.has(groupName)) grouped.set(groupName, []);
                grouped.get(groupName).push({ ...row, label: row.path[row.path.length - 1] });
            }
            return [...grouped.entries()].map(([name, groupRows]) => ({ name, rows: groupRows }));
        });
        const pivotTables = computed(() => {
            if (!activeReport.value?.benchmark) return [];
            const grouped = new Map();
            for (const row of flatten(activeReport.value.benchmark)) {
                if (row.path.length < 2) continue;
                const groupName = row.path.slice(0, -2).join(" / ") || "Benchmark";
                const rowLabel = row.path[row.path.length - 2];
                const column = row.path[row.path.length - 1];
                if (!grouped.has(groupName)) grouped.set(groupName, { columns: [], rows: new Map() });
                const table = grouped.get(groupName);
                if (!table.columns.includes(column)) table.columns.push(column);
                if (!table.rows.has(rowLabel)) table.rows.set(rowLabel, { label: rowLabel, cells: {} });
                table.rows.get(rowLabel).cells[column] = row.value;
            }
            return [...grouped.entries()].map(([name, table]) => compactTable(markTopPerformer({ name, columns: table.columns, rows: [...table.rows.values()] })));
        });
        const allRows = computed(() => suites.value.flatMap(suite => {
            const report = diff.value.reports[suite];
            return report.status === "matched" ? flatten(report.benchmark) : [];
        }));
        const changedCount = computed(() => allRows.value.filter(row => row.value.delta !== 0).length);
        const largestChange = computed(() => {
            const row = allRows.value.reduce((largest, current) => Math.abs(current.value.percent_change ?? 0) > Math.abs(largest?.value.percent_change ?? 0) ? current : largest, null);
            return row ? formatPercent(row.value.percent_change) : "none";
        });

        return { diff, error, activeSuite, activeReport, suites, rows, pivotTables, view, suiteCount: computed(() => suites.value.length), changedCount, largestChange, isLight, toggleTheme, loadDiff, shortPath, formatValue, formatPercent, changeClass, rowClasses, sortTable, sortRows, sortIndicator, columnLabel, columnDescription, rankingDirection };
    }
}).mount("#app");
