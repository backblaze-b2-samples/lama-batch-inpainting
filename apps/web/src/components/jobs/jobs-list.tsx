"use client";

import Link from "next/link";
import { Wand2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { JobStatusBadge } from "./job-status-badge";
import { useJobs } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function JobsList() {
  const { data: jobs = [], isLoading, error, refetch } = useJobs();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState
            error={error}
            title="Couldn't load jobs"
            onRetry={() => refetch()}
          />
        </CardContent>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-3 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={Wand2}
            title="No jobs yet"
            description="Create a job from your paired source images to run LaMa inpainting."
            action={
              <Button asChild size="sm">
                <Link href="/jobs/new">
                  <Wand2 aria-hidden="true" className="h-3.5 w-3.5" />
                  New job
                </Link>
              </Button>
            }
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table className="table-fixed">
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="w-[38%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Job
              </TableHead>
              <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Images
              </TableHead>
              <TableHead className="w-[18%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Status
              </TableHead>
              <TableHead className="w-[30%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Created
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id} className="table-row-hover">
                <TableCell className="font-medium">
                  <Link
                    href={`/jobs/${job.id}`}
                    className="block truncate hover:underline"
                    title={job.label ?? job.id}
                  >
                    {job.label ?? `Job ${job.id.slice(0, 8)}`}
                  </Link>
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {job.pairs.length}
                </TableCell>
                <TableCell>
                  <JobStatusBadge status={job.status} />
                </TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">
                  {formatDate(job.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
