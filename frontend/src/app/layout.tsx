import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

const BASE = "https://policonomy-nine.vercel.app";

export const metadata: Metadata = {
  title: "Policonomy",
  description: "AI 정치·경제 분석 & 예측 대시보드",
  metadataBase: new URL(BASE),
  openGraph: {
    title: "Policonomy",
    description: "AI 정치·경제 분석 & 예측 대시보드",
    url: BASE,
    siteName: "Policonomy",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: "Policonomy",
    description: "AI 정치·경제 분석 & 예측 대시보드",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className={`${geist.className} bg-gray-950 text-gray-100 min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
