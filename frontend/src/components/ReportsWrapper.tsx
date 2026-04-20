"use client";

import dynamic from "next/dynamic";

const ReportsClient = dynamic(() => import("./ReportsClient"), { ssr: false });

export default function ReportsWrapper() {
  return <ReportsClient />;
}
