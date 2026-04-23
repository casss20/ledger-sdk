import { useFilters } from "../../hooks/useFilters";

export function AuditFilters() {
  const { getFilter, setFilter, clearFilters } = useFilters();

  return (
    <div className="filter-row card">
      <div className="filter-row__group">
        <input 
          className="search-input" 
          placeholder="Search trace ID, actor, target" 
          value={getFilter("q")}
          onChange={(e) => setFilter("q", e.target.value)}
        />
        <select 
          className="select-input"
          value={getFilter("env", "all")}
          onChange={(e) => setFilter("env", e.target.value)}
        >
          <option value="all">All environments</option>
          <option value="production">Production</option>
          <option value="staging">Staging</option>
        </select>
        <select 
          className="select-input"
          value={getFilter("outcome", "all")}
          onChange={(e) => setFilter("outcome", e.target.value)}
        >
          <option value="all">All outcomes</option>
          <option value="allowed">Allowed</option>
          <option value="blocked">Blocked</option>
          <option value="escalated">Escalated</option>
        </select>
      </div>
      <div style={{ display: "flex", gap: "12px" }}>
        <button className="btn btn-secondary" onClick={clearFilters}>
          Clear
        </button>
        <button className="btn btn-secondary">Export JSON</button>
      </div>
    </div>
  );
}
