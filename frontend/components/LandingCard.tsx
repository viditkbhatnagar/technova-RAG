import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface LandingCardProps {
  icon: string;
  title: string;
  description: string;
  href: string;
  accent: string;
}

export function LandingCard({ icon, title, description, href, accent }: LandingCardProps) {
  return (
    <Link href={href} className="group block">
      <Card
        className={`relative h-full overflow-hidden border-base bg-surface-1 shadow-card backdrop-blur-md transition-all duration-300 hover:-translate-y-1 hover:border-strong hover:bg-surface-2`}
      >
        <div
          className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
          style={{
            background: `radial-gradient(600px circle at 50% 0%, ${accent}20, transparent 50%)`,
          }}
        />
        <CardHeader className="relative">
          <div
            className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl border text-2xl"
            style={{ borderColor: `${accent}50`, background: `${accent}15` }}
          >
            {icon}
          </div>
          <CardTitle className="text-2xl tracking-tight text-strong">{title}</CardTitle>
          <CardDescription className="text-sm leading-relaxed text-muted-fg">
            {description}
          </CardDescription>
        </CardHeader>
        <CardContent className="relative">
          <span
            className="inline-flex items-center gap-1.5 text-sm font-medium transition-colors"
            style={{ color: accent }}
          >
            Explore
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}
