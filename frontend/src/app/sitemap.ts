import type { MetadataRoute } from "next";

const BASE = "https://policonomy-nine.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE, lastModified: new Date(), changeFrequency: "daily", priority: 1 },
    { url: `${BASE}/reports`, lastModified: new Date(), changeFrequency: "daily", priority: 0.9 },
    { url: `${BASE}/insights`, lastModified: new Date(), changeFrequency: "daily", priority: 0.8 },
    { url: `${BASE}/newsletter`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.7 },
    { url: `${BASE}/privacy`, lastModified: new Date(), changeFrequency: "yearly", priority: 0.3 },
  ];
}
