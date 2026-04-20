"use client";

import { UserSettings } from "@/lib/api";
import { useState } from "react";

const CATEGORY_OPTIONS = [
  { id: "politics_economy", label: "정치·경제" },
  { id: "global_macro", label: "글로벌" },
  { id: "tech_industry", label: "테크" },
  { id: "real_estate", label: "부동산" },
];


interface SettingsFormProps {
  data: UserSettings;
  onSubmit: (data: UserSettings) => Promise<void>;
}

export default function SettingsForm({ data, onSubmit }: SettingsFormProps) {
  const [form, setForm] = useState<UserSettings>(data);
  const [loading, setLoading] = useState(false);

  const handleCategoryChange = (category: string, checked: boolean) => {
    setForm({
      ...form,
      categories: checked
        ? [...form.categories, category]
        : form.categories.filter((c) => c !== category),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onSubmit(form);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 뉴스레터 카테고리 */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h3 className="text-sm font-medium text-gray-300 mb-4">뉴스레터 카테고리</h3>
        <div className="space-y-3">
          {CATEGORY_OPTIONS.map((cat) => (
            <label key={cat.id} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.categories.includes(cat.id)}
                onChange={(e) => handleCategoryChange(cat.id, e.target.checked)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-600 cursor-pointer"
              />
              <span className="text-sm text-gray-300">{cat.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* 이메일 설정 */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h3 className="text-sm font-medium text-gray-300 mb-4">이메일 설정</h3>
        <div className="space-y-4">
          <div>
            <label className="block">
              <span className="text-xs text-gray-400 font-medium mb-2 block">이메일 주소</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-300 placeholder-gray-600"
                placeholder="user@example.com"
              />
            </label>
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.email_notifications}
              onChange={(e) => setForm({ ...form, email_notifications: e.target.checked })}
              className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-600 cursor-pointer"
            />
            <span className="text-sm text-gray-300">이메일 알림 활성화</span>
          </label>
        </div>
      </div>

      {/* 저장 버튼 */}
      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg text-sm font-medium text-white transition-colors"
      >
        {loading ? "저장 중..." : "저장"}
      </button>
    </form>
  );
}
