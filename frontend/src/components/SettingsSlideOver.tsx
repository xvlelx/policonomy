"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, UserSettings } from "@/lib/api";
import SettingsForm from "./SettingsForm";

type Props = {
  open: boolean;
  onClose: () => void;
};

export default function SettingsSlideOver({ open, onClose }: Props) {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (open && !settings) {
      setLoading(true);
      api.settings()
        .then(setSettings)
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [open, settings]);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const handleSave = async (data: UserSettings) => {
    await api.updateSettings(data);
    setSettings(data);
    setToast("저장됨 ✓");
    setTimeout(() => setToast(null), 2000);
  };

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/60 z-40"
        onClick={onClose}
      />
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-gray-950 border-l border-gray-800 flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800 flex-shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-gray-100">설정</h2>
            <p className="text-xs text-gray-400 mt-0.5">뉴스레터 및 알림 설정</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors p-1"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          {settings && !loading && (
            <SettingsForm data={settings} onSubmit={handleSave} />
          )}
          {!settings && !loading && (
            <p className="text-xs text-gray-400 text-center py-12">설정을 불러올 수 없습니다.</p>
          )}
        </div>

        {toast && (
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm shadow-lg">
            {toast}
          </div>
        )}
      </div>
    </>
  );
}
