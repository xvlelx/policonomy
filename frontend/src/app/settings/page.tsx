"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, UserSettings } from "@/lib/api";
import SettingsForm from "@/components/SettingsForm";

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await api.settings();
        setSettings(data);
      } catch (e) {
        setError("설정을 불러올 수 없습니다.");
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async (data: UserSettings) => {
    try {
      await api.updateSettings(data);
      setSettings(data);
      setError(null);
      setToast("저장됨 ✓");
      setTimeout(() => setToast(null), 2000);
    } catch (e) {
      setError("저장에 실패했습니다.");
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <div className="text-gray-400 text-sm">설정 불러오는 중...</div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-red-400">{error || "설정을 불러올 수 없습니다."}</div>
        <Link href="/" className="px-4 py-2 bg-blue-600 rounded-lg text-sm">
          대시보드로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <Link
          href="/"
          className="text-xs text-gray-400 hover:text-gray-300 mb-4 inline-block"
        >
          ← 대시보드로 돌아가기
        </Link>
        <h1 className="text-2xl font-bold text-gray-100">설정</h1>
        <p className="text-gray-400 text-sm mt-1">뉴스레터 및 알림 설정을 관리하세요.</p>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-4 p-3 bg-red-900 border border-red-700 rounded-lg text-sm text-red-200">
          {error}
        </div>
      )}

      {/* 토스트 메시지 */}
      {toast && (
        <div className="fixed bottom-4 right-4 px-4 py-2 bg-green-600 text-white rounded-lg text-sm animate-pulse">
          {toast}
        </div>
      )}

      {/* 설정 폼 */}
      <SettingsForm data={settings} onSubmit={handleSave} />
    </div>
  );
}
