type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  description?: string;
};

export function SectionHeader({ eyebrow, title, subtitle, description }: SectionHeaderProps) {
  const supportingText = description || subtitle;

  return (
    <div className="page-shell__header">
      <div>
        {eyebrow ? <p>{eyebrow}</p> : null}
        <h2>{title}</h2>
        {supportingText ? <p>{supportingText}</p> : null}
      </div>
    </div>
  );
}
