import { JobCreateForm } from "@/components/jobs/job-create-form";

export default function NewJobPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New Job</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Select the source images to inpaint. This creates a pending job — run
          it from the job page to invoke LaMa over each source/mask pair.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <JobCreateForm />
      </div>
    </div>
  );
}
