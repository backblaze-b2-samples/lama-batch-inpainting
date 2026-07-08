"use client";

import { Wand2, Images, CheckCircle2, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { useInpaintingStats } from "@/lib/queries";

export function InpaintingStatsCards() {
  const { data: stats, isLoading, error, refetch } = useInpaintingStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    { title: "Total Jobs", value: stats?.total_jobs ?? 0, icon: Wand2 },
    {
      title: "Images Inpainted",
      value: stats?.images_inpainted ?? 0,
      icon: Images,
    },
    { title: "Approved", value: stats?.approved_count ?? 0, icon: CheckCircle2 },
    {
      title: "Storage Amplification",
      value: stats ? `${stats.amplification_ratio.toFixed(2)}×` : "—",
      icon: Layers,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
