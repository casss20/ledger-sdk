import { useFilters } from "../../hooks/useFilters";

export function ApprovalFilters() {
  const { getFilter, setFilter, clearFilters } = useFilters();

  return (
    <div className="filter-row card">
      <div className="filter-row__group">
        <input 
          className="search-input" 
          placeholder="Search requests"
          value={getFilter("q")}
          onChange={(e) => setFilter("q", e.target.value)}
        />
        <select 
          className="select-input"
          value={getFilter("risk", "all")}
          onChange={(e) => setFilter("risk", e.target.value)}
        >
          <option value="all">All risks</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select 
          className="select-input"
          value={getFilter("status", "all")}
          onChange={(e) => setFilter("status", e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="blocked">Blocked</option>
        </select>
      </div>
      <button className="btn btn-secondary" onClick={clearFilters}>
        Clear filters
      </button>
    </div>
  );
}
