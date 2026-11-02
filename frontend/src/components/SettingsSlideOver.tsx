"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, ApiError, UserSettings } from "@/lib/api";
import SettingsForm from "./SettingsForm";

type Props = {
  open: boolean;
  onClose: () => void;
};

export default function SettingsSlideOver({ open, onClose }: Props) {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [toast, setToast] = useState<{ message: string; ok: boolean } | null>(null);
  // 열려 있고 아직 설정을 못 받았으며 실패하지 않은 상태면 로딩 중
  const loading = open && !settings && !loadFailed;

  useEffect(() => {
    if (!open || settings || loadFailed) return;
    let cancelled = false;
    api.settings()
      .then((data) => { if (!cancelled) setSettings(data); })
      .catch(() => { if (!cancelled) setLoadFailed(true); });
    return () => { cancelled = true; };
  }, [open, settings, loadFailed]);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const handleSave = async (data: UserSettings) => {
    try {
      await api.updateSettings(data);
      setSettings(data);
      setToast({ message: "저장됨 ✓", ok: true });
    } catch (e) {
      const forbidden = e instanceof ApiError && e.status === 403;
      setToast({
        message: forbidden ? "설정 저장은 관리자만 가능합니다" : "저장에 실패했습니다. 다시 시도해주세요.",
        ok: false,
      });
    }
    setTimeout(() => setToast(null), 2500);
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
            aria-label="닫기"
            className="-mr-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-gray-500 hover:text-gray-300 transition-colors"
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
            <div className="text-center py-12">
              <p className="text-xs text-gray-400">설정을 불러올 수 없습니다.</p>
              {loadFailed && (
                <button
                  type="button"
                  onClick={() => setLoadFailed(false)}
                  className="mt-3 min-h-[44px] px-4 text-xs text-blue-400 hover:text-blue-300"
                >
                  다시 시도
                </button>
              )}
            </div>
          )}
        </div>

        {toast && (
          <div
            role="status"
            className={`absolute bottom-[calc(1.5rem+env(safe-area-inset-bottom))] left-1/2 -translate-x-1/2 px-4 py-2 text-white rounded-lg text-sm shadow-lg ${
              toast.ok ? "bg-green-600" : "bg-red-600"
            }`}
          >
            {toast.message}
          </div>
        )}
      </div>
    </>
  );
}
