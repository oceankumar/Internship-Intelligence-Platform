import { Platform } from "../components/platform";
export const dynamic = "force-dynamic";

export default function Home() {
  return <Platform demo={process.env.PUBLIC_DEMO_MODE === "true"} />;
}
