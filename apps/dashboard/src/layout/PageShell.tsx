import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function PageShell({ title, description, actions, children }: Props) {
  return (
    <section className="page-shell">
      <div className="page-shell__header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
      <div className="page-shell__body">{children}</div>
    </section>
  );
}
