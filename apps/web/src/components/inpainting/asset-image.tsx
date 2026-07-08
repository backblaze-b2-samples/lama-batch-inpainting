"use client";

import Image from "next/image";
import { ImageOff } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssetUrl } from "@/lib/queries";

interface AssetImageProps {
  assetKey: string | null | undefined;
  alt: string;
  className?: string;
}

/**
 * Renders a B2 object inline via a short-lived presigned URL. `unoptimized`
 * because presigned URLs carry their own expiry and shouldn't be cached by
 * Next's image optimizer past that window.
 */
export function AssetImage({ assetKey, alt, className }: AssetImageProps) {
  const { data, isLoading, isError } = useAssetUrl(assetKey ?? undefined);
  const url = data?.url ?? null;

  const wrap =
    "relative aspect-square w-full overflow-hidden rounded-md border border-border bg-muted/30";

  if (!assetKey) {
    return (
      <div className={`${wrap} ${className ?? ""}`}>
        <div className="absolute inset-0 grid place-items-center text-muted-foreground">
          <ImageOff className="h-6 w-6" aria-hidden="true" />
        </div>
      </div>
    );
  }

  return (
    <div className={`${wrap} ${className ?? ""}`}>
      {isLoading ? (
        <Skeleton className="absolute inset-0 h-full w-full" />
      ) : isError || !url ? (
        <div className="absolute inset-0 grid place-items-center text-muted-foreground">
          <ImageOff className="h-6 w-6" aria-hidden="true" />
        </div>
      ) : (
        <Image
          src={url}
          alt={alt}
          fill
          sizes="(max-width: 768px) 50vw, 300px"
          className="object-contain"
          unoptimized
        />
      )}
    </div>
  );
}
