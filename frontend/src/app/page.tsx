import { Suspense } from "react";
import DashboardClient from "@/components/DashboardClient";

export default function Home() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen text-gray-400">로딩 중...</div>}>
      <DashboardClient />
    </Suspense>
  );
}
