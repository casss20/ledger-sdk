import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
};

export function Card({ title, children }: Props) {
  return (
    <section className="card">
      {title ? <div className="card__title">{title}</div> : null}
      <div className="card__body">{children}</div>
    </section>
  );
}
