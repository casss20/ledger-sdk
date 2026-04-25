type Props = {
  onOpenCommandBar?: () => void;
};

export function Topbar({ onOpenCommandBar }: Props) {
  return (
    <header className="topbar">
      <div>
        <h1>Citadel Governance</h1>
        <p>Runtime controls and audit visibility</p>
      </div>

      <div className="topbar__actions">
        <input
          className="search-input"
          placeholder="Search trace, agent, policy... (Cmd+K)"
          onClick={onOpenCommandBar}
          readOnly
        />
        <button className="btn btn-secondary">Last 24 hours</button>
        <button className="btn btn-primary">Export</button>
      </div>
    </header>
  );
}
