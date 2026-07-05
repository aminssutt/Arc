import { Button, ButtonVariant, ButtonSize } from "@/components/Button";
import { Badge, BadgeTone } from "@/components/Badge";
import { Card } from "@/components/Card";

const BUTTON_VARIANTS: { name: string; value: ButtonVariant }[] = [
  { name: "Primary", value: "primary" },
  { name: "Secondary", value: "secondary" },
  { name: "Ghost", value: "ghost" },
  { name: "Warning", value: "warning" },
  { name: "Warning Subtle", value: "warningSubtle" },
];

const BUTTON_SIZES: { name: string; value: ButtonSize }[] = [
  { name: "Small", value: "sm" },
  { name: "Medium", value: "md" },
  { name: "Large", value: "lg" },
];

const BADGE_TONES: { name: string; value: BadgeTone }[] = [
  { name: "Primary", value: "primary" },
  { name: "Secondary", value: "secondary" },
  { name: "Warning", value: "warning" },
  { name: "Neutral", value: "neutral" },
];

function Section({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="text-h4 font-semibold text-text">{title}</h2>
        <p className="text-caption text-muted">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

export default function DesignReviewPage() {
  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-10 p-8">
      <header>
        <p className="text-label-sm font-medium uppercase tracking-wide text-accent">Arc Design Review</p>
        <h1 className="text-h2 font-bold text-text">Component library</h1>
        <p className="mt-1 text-body-sm text-muted">
          Pulled from Figma file 8AFA0Or97IrnY7QSLJwKHQ — Foundations, Button, Badge, Card sections.
        </p>
      </header>

      <Section title="Button" subtitle="Style x Size x State — Figma node 38:6">
        <div className="flex flex-col gap-4">
          {BUTTON_VARIANTS.map(({ name, value }) => (
            <div key={value} className="flex flex-col gap-2">
              <p className="text-label text-muted">{name}</p>
              <div className="flex flex-wrap items-center gap-3">
                {BUTTON_SIZES.map(({ name: sizeName, value: sizeValue }) => (
                  <Button key={sizeValue} variant={value} size={sizeValue}>
                    {sizeName}
                  </Button>
                ))}
                <Button variant={value} size="sm" disabled>
                  Disabled
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Badge" subtitle="Tone x Emphasis — Figma node 38:8">
        <div className="flex flex-col gap-3">
          {BADGE_TONES.map(({ name, value }) => (
            <div key={value} className="flex items-center gap-4">
              <p className="w-24 text-label text-muted">{name}</p>
              <Badge tone={value} emphasis="solid">
                Active
              </Badge>
              <Badge tone={value} emphasis="subtle">
                Active
              </Badge>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Card" subtitle="Base surface — Figma node 38:9">
        <Card eyebrow="Arc Card" title="Investigation summary" footnote="Variable-bound surface" className="max-w-[360px]">
          A compact surface for timeline items, evidence snapshots, and agent status blocks.
        </Card>
      </Section>
    </main>
  );
}
