import { notFound } from "next/navigation";
import { Platform } from "../../components/platform";

export default async function WorkspacePage({
  params,
}: {
  params: Promise<{ view: string }>;
}) {
  const { view } = await params;
  if (
    ![
      "discover",
      "saved",
      "applications",
      "insights",
      "sources",
      "profile",
    ].includes(view)
  )
    notFound();
  return <Platform view={view} demo={process.env.PUBLIC_DEMO_MODE === "true"} />;
}
