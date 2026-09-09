interface DashboardPageProps {
  title: string;
  eyebrow: string;
  description: string;
}

export function DashboardPage({ title, eyebrow, description }: DashboardPageProps) {
  return (
    <section className="foundation-page" aria-labelledby="page-title">
      <p className="eyebrow">{eyebrow}</p>
      <h1 id="page-title">{title}</h1>
      <div className="foundation-state">
        <h2>Foundation ready</h2>
        <p>{description} Live operational data will appear here as its connected workspace becomes available.</p>
      </div>
    </section>
  );
}
