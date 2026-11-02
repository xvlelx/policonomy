import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "개인정보처리방침 | Policonomy",
  description: "Policonomy 개인정보처리방침",
};

export default function PrivacyPage() {
  const updated = "2026년 4월 22일";

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 text-gray-300 space-y-8">
      <div>
        <Link
          href="/"
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          ← 대시보드
        </Link>
        <h1 className="text-2xl font-bold text-gray-100 mt-4">개인정보처리방침</h1>
        <p className="text-xs text-gray-500 mt-1">최종 수정일: {updated}</p>
      </div>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">1. 수집하는 개인정보</h2>
        <p className="text-sm leading-relaxed">
          Policonomy는 뉴스레터 구독 신청 시 다음 정보를 수집합니다.
        </p>
        <ul className="text-sm leading-relaxed list-disc pl-5 space-y-1 text-gray-400">
          <li>이메일 주소 (필수)</li>
          <li>이름 (선택)</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">2. 개인정보의 이용 목적</h2>
        <ul className="text-sm leading-relaxed list-disc pl-5 space-y-1 text-gray-400">
          <li>뉴스레터 발송 (매일 오전 AI 경제 브리핑)</li>
          <li>구독 확인 및 수신거부 처리</li>
          <li>서비스 장애·공지 안내</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">3. 개인정보 보유 기간</h2>
        <p className="text-sm leading-relaxed text-gray-400">
          구독 해지 요청 시 즉시 비활성화 처리하며, 관련 법령에 따른 보존 의무가 없는 경우
          요청일로부터 30일 이내 완전 삭제합니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">4. 제3자 제공</h2>
        <p className="text-sm leading-relaxed text-gray-400">
          수집된 개인정보는 제3자에게 제공, 공유, 판매하지 않습니다.
          단, 이메일 발송을 위해 AWS Simple Email Service(SES)를 이용하며,
          이메일 주소는 발송 목적으로만 사용됩니다.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">5. 수신거부 방법</h2>
        <p className="text-sm leading-relaxed text-gray-400">
          뉴스레터 하단의 &lsquo;수신거부&rsquo; 링크를 클릭하거나,
          아래 이메일로 수신거부 요청을 보내주시면 즉시 처리합니다.
        </p>
        <p className="text-sm text-blue-400">xvlelx84@gmail.com</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">6. 개인정보 보호책임자</h2>
        <ul className="text-sm leading-relaxed text-gray-400 space-y-1">
          <li>서비스명: Policonomy</li>
          <li>문의: xvlelx84@gmail.com</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-200">7. 면책 고지</h2>
        <p className="text-sm leading-relaxed text-gray-400">
          본 서비스에서 제공하는 모든 분석 및 예측은 AI가 생성한 정보로,
          투자 권유 또는 금융 조언이 아닙니다.
          투자 결정은 본인의 판단과 책임하에 이루어져야 합니다.
        </p>
      </section>

      <p className="text-xs text-gray-600 pt-4 border-t border-gray-800">
        본 방침은 관련 법령 또는 서비스 변경 시 사전 고지 없이 개정될 수 있습니다.
      </p>
    </div>
  );
}
