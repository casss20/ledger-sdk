export function KillSwitchPanel() {
  return (
    <section className="card emergency-panel">
      <div className="emergency-panel__eyebrow">Emergency controls</div>
      <h3>Revoke all active agent permissions</h3>
      <p>
        Immediately suspend execution access for connected agents across the selected scope.
      </p>

      <div className="stack-md">
        <label className="field">
          <span>Scope</span>
          <select className="select-input">
            <option>All agents / production</option>
            <option>Selected agents only</option>
            <option>GitHub integration only</option>
            <option>Payments only</option>
          </select>
        </label>

        <label className="field">
          <span>Type REVOKE ALL</span>
          <input className="text-input" placeholder="REVOKE ALL" />
        </label>
      </div>

      <div className="emergency-panel__actions">
        <button className="btn btn-danger">Execute kill switch</button>
      </div>
    </section>
  );
}
