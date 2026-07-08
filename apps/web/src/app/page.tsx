import Link from "next/link";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { InpaintingStatsCards } from "@/components/dashboard/inpainting-stats-cards";
import { RecentJobsTable } from "@/components/dashboard/recent-jobs-table";
import { PrefixBytesChart } from "@/components/dashboard/prefix-bytes-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Batch LaMa inpainting on Backblaze B2 — every source keeps its mask
            and gains a full-resolution output.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/jobs/new">
            <Wand2 className="h-3.5 w-3.5" />
            New job
          </Link>
        </Button>
      </div>
      <InpaintingStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <PrefixBytesChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentJobsTable />
        </div>
      </div>
    </div>
  );
}
