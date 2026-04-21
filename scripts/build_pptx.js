const pptxgen = require("pptxgenjs");

// ── Color Palette ──
const C = {
  bg:       "0F1419",   // deep black
  bgCard:   "1A2332",   // card bg
  bgCard2:  "1E293B",   // lighter card
  accent:   "3B82F6",   // blue accent
  accent2:  "10B981",   // green accent
  accent3:  "F59E0B",   // amber accent
  red:      "EF4444",   // red/danger
  white:    "FFFFFF",
  text1:    "F1F5F9",   // primary text
  text2:    "94A3B8",   // secondary text
  text3:    "64748B",   // muted text
  border:   "334155",   // subtle border
};

const FONT_H = "Arial Black";
const FONT_B = "Arial";

// ── Helpers ──
const makeShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.3 });

function addSlideNumber(slide, num, total) {
  slide.addText(`${num} / ${total}`, {
    x: 8.8, y: 5.2, w: 1, h: 0.3,
    fontSize: 9, color: C.text3, fontFace: FONT_B, align: "right",
  });
}

function addCard(slide, x, y, w, h) {
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: C.bgCard },
    shadow: makeShadow(),
  });
}

function addAccentCard(slide, x, y, w, h, accentColor) {
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: C.bgCard },
    shadow: makeShadow(),
  });
  slide.addShape("rect", {
    x, y, w: 0.06, h,
    fill: { color: accentColor },
  });
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Edwin";
  pres.title = "MeetingMind — 언제 생각할지 판단하는 회의 AI";
  const TOTAL = 11;

  // ════════════════════════════════════════════════════════════
  // SLIDE 1: Title
  // ════════════════════════════════════════════════════════════
  let s1 = pres.addSlide();
  s1.background = { color: C.bg };

  // Top accent line
  s1.addShape("rect", { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s1.addText("MeetingMind", {
    x: 0.8, y: 1.2, w: 8.4, h: 1.0,
    fontSize: 48, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
  });
  s1.addText("회의 AI는 매번 생각하면 안 된다", {
    x: 0.8, y: 2.2, w: 8.4, h: 0.7,
    fontSize: 26, fontFace: FONT_B, color: C.accent, margin: 0,
  });
  s1.addText("언제 개입하고, 언제 검색하고, 언제 분석할지를\n판단하는 것이 핵심이다", {
    x: 0.8, y: 3.0, w: 8.4, h: 1.0,
    fontSize: 16, fontFace: FONT_B, color: C.text2, lineSpacingMultiple: 1.5, margin: 0,
  });

  // Bottom bar
  s1.addShape("rect", { x: 0, y: 5.1, w: 10, h: 0.525, fill: { color: C.bgCard } });
  s1.addText("실시간 음성 회의 분석 시스템  |  로컬 퍼스트  |  Apple Silicon MLX", {
    x: 0.8, y: 5.15, w: 8.4, h: 0.45,
    fontSize: 11, fontFace: FONT_B, color: C.text3, valign: "middle",
  });
  addSlideNumber(s1, 1, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 2: Problem — "매 발화마다 LLM을 호출하면?"
  // ════════════════════════════════════════════════════════════
  let s2 = pres.addSlide();
  s2.background = { color: C.bg };

  s2.addText("PROBLEM", {
    x: 0.8, y: 0.4, w: 2, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.red, bold: true, charSpacing: 3, margin: 0,
  });
  s2.addText("매 발화마다 LLM을 호출하면?", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });

  // Pipeline cost breakdown — 3 cards
  const costs = [
    { label: "토픽 판단", time: "0.5 ~ 2s", color: C.accent },
    { label: "쟁점 분석", time: "1 ~ 3s", color: C.accent3 },
    { label: "엔티티 추출", time: "0.5 ~ 2s", color: C.accent2 },
  ];
  costs.forEach((c, i) => {
    const cx = 0.8 + i * 2.9;
    addAccentCard(s2, cx, 1.6, 2.6, 1.1, c.color);
    s2.addText(c.label, {
      x: cx + 0.25, y: 1.7, w: 2.2, h: 0.35,
      fontSize: 13, fontFace: FONT_B, color: C.text2, margin: 0,
    });
    s2.addText(c.time, {
      x: cx + 0.25, y: 2.05, w: 2.2, h: 0.5,
      fontSize: 24, fontFace: FONT_H, color: c.color, bold: true, margin: 0,
    });
  });

  // Arrow + total
  s2.addText("=  발화당 2 ~ 7초 지연", {
    x: 0.8, y: 2.95, w: 8.4, h: 0.5,
    fontSize: 18, fontFace: FONT_B, color: C.red, bold: true, margin: 0,
  });

  // Impact cards
  addCard(s2, 0.8, 3.7, 4.0, 1.2);
  s2.addText("30분 회의", {
    x: 1.1, y: 3.8, w: 3.5, h: 0.3,
    fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
  });
  s2.addText("LLM 540회 호출", {
    x: 1.1, y: 4.1, w: 3.5, h: 0.5,
    fontSize: 26, fontFace: FONT_H, color: C.red, bold: true, margin: 0,
  });

  addCard(s2, 5.2, 3.7, 4.0, 1.2);
  s2.addText("180발화 × 3회/발화", {
    x: 5.5, y: 3.8, w: 3.5, h: 0.3,
    fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
  });
  s2.addText("로컬 환경에서 불가능", {
    x: 5.5, y: 4.1, w: 3.5, h: 0.5,
    fontSize: 22, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
  });

  addSlideNumber(s2, 2, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 3: Solution Overview
  // ════════════════════════════════════════════════════════════
  let s3 = pres.addSlide();
  s3.background = { color: C.bg };

  s3.addText("SOLUTION", {
    x: 0.8, y: 0.4, w: 2, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent, bold: true, charSpacing: 3, margin: 0,
  });
  s3.addText("3가지 판단 설계", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });
  s3.addText('"LLM을 쓸 수 있다"가 아니라 "LLM을 안 쓰는 판단"이 핵심', {
    x: 0.8, y: 1.35, w: 8.4, h: 0.4,
    fontSize: 14, fontFace: FONT_B, color: C.text2, italic: true, margin: 0,
  });

  const solutions = [
    { num: "01", title: "90%는 생각하지 않는다", sub: "토픽 감지 3단계 필터", desc: "키워드 → 복합키워드 → LLM\n94.5% 발화에서 LLM 호출 0", color: C.accent },
    { num: "02", title: "정보량을 측정한다", sub: "토큰 기반 쟁점 구조화", desc: "발화 수가 아닌 문자 누적량 기준\nLLM 호출 40% 감소", color: C.accent3 },
    { num: "03", title: "동의 중이면 검색 안 한다", sub: "부동의 기반 자료 수집", desc: "의견 대립 시에만 검색 트리거\n웹검색 75% 감소", color: C.accent2 },
  ];

  solutions.forEach((s, i) => {
    const cy = 2.0 + i * 1.15;
    addAccentCard(s3, 0.8, cy, 8.4, 1.0, s.color);
    s3.addText(s.num, {
      x: 1.1, y: cy + 0.1, w: 0.6, h: 0.8,
      fontSize: 28, fontFace: FONT_H, color: s.color, bold: true, valign: "middle", margin: 0,
    });
    s3.addText(s.title, {
      x: 1.8, y: cy + 0.12, w: 4, h: 0.35,
      fontSize: 17, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
    });
    s3.addText(s.sub, {
      x: 1.8, y: cy + 0.5, w: 4, h: 0.3,
      fontSize: 12, fontFace: FONT_B, color: C.text2, margin: 0,
    });
    s3.addText(s.desc, {
      x: 6.0, y: cy + 0.1, w: 3.0, h: 0.8,
      fontSize: 11, fontFace: FONT_B, color: C.text3, lineSpacingMultiple: 1.4, valign: "middle", margin: 0,
    });
  });

  addSlideNumber(s3, 3, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 4: Solution 1 — 토픽 감지 3단계 필터
  // ════════════════════════════════════════════════════════════
  let s4 = pres.addSlide();
  s4.background = { color: C.bg };

  s4.addText("01", {
    x: 0.8, y: 0.4, w: 1, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent, bold: true, charSpacing: 3, margin: 0,
  });
  s4.addText("90%는 생각하지 않는다", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });
  s4.addText("토픽 감지 3단계 필터 — LLM 호출을 최소화하는 구조", {
    x: 0.8, y: 1.35, w: 8.4, h: 0.3,
    fontSize: 13, fontFace: FONT_B, color: C.text2, margin: 0,
  });

  // Funnel stages
  const stages = [
    { label: "Stage 1", title: '키워드 매칭', detail: '"다음 안건", "넘어가서" 등', cost: "0ms", pct: "~90% 탈락", color: C.accent, w: 8.4 },
    { label: "Stage 2", title: '복합 키워드 (2개+)', detail: '키워드 2개 이상 → LLM 없이 즉시 판정', cost: "0ms", pct: "~4.5% 즉시 처리", color: C.accent3, w: 6.8 },
    { label: "Stage 3", title: 'LLM 판정', detail: '최근 10발화 컨텍스트 → 토픽 변경 여부 판단', cost: "0.5~2s", pct: "~5.5%만 호출", color: C.red, w: 4.4 },
  ];

  stages.forEach((st, i) => {
    const cy = 1.9 + i * 1.15;
    const cx = 0.8 + (8.4 - st.w) / 2;
    addAccentCard(s4, cx, cy, st.w, 1.0, st.color);
    s4.addText(st.label, {
      x: cx + 0.25, y: cy + 0.08, w: 1.2, h: 0.3,
      fontSize: 10, fontFace: FONT_B, color: st.color, bold: true, margin: 0,
    });
    s4.addText(st.title, {
      x: cx + 0.25, y: cy + 0.35, w: st.w - 2.5, h: 0.3,
      fontSize: 15, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
    });
    s4.addText(st.detail, {
      x: cx + 0.25, y: cy + 0.65, w: st.w - 2.5, h: 0.25,
      fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
    });
    // Right side stats
    s4.addText(st.cost, {
      x: cx + st.w - 2.2, y: cy + 0.1, w: 1.8, h: 0.35,
      fontSize: 16, fontFace: FONT_H, color: st.color, bold: true, align: "right", margin: 0,
    });
    s4.addText(st.pct, {
      x: cx + st.w - 2.2, y: cy + 0.55, w: 1.8, h: 0.3,
      fontSize: 11, fontFace: FONT_B, color: C.text2, align: "right", margin: 0,
    });
  });

  // Result
  addCard(s4, 0.8, 5.0, 8.4, 0.45);
  s4.addText([
    { text: "결과: ", options: { bold: true, color: C.text2 } },
    { text: "180발화 중 LLM 호출은 약 10회", options: { color: C.accent, bold: true } },
    { text: "  →  94.5%의 발화에서 LLM 비용 0, 지연 0", options: { color: C.text2 } },
  ], {
    x: 1.1, y: 5.05, w: 7.9, h: 0.35,
    fontSize: 13, fontFace: FONT_B, valign: "middle", margin: 0,
  });

  addSlideNumber(s4, 4, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 5: Solution 2 — 토큰 기반 쟁점 구조화
  // ════════════════════════════════════════════════════════════
  let s5 = pres.addSlide();
  s5.background = { color: C.bg };

  s5.addText("02", {
    x: 0.8, y: 0.4, w: 1, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent3, bold: true, charSpacing: 3, margin: 0,
  });
  s5.addText("정보량을 측정한다", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });

  // Before/After comparison
  // Before
  addAccentCard(s5, 0.8, 1.6, 4.0, 2.5, C.red);
  s5.addText("BEFORE", {
    x: 1.1, y: 1.7, w: 2, h: 0.3,
    fontSize: 10, fontFace: FONT_B, color: C.red, bold: true, charSpacing: 2, margin: 0,
  });
  s5.addText("발화 수 기준 배치", {
    x: 1.1, y: 2.0, w: 3.4, h: 0.35,
    fontSize: 16, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
  });
  s5.addText([
    { text: '10발화마다 LLM 호출', options: { breakLine: true, color: C.text2 } },
    { text: '', options: { breakLine: true, fontSize: 6 } },
    { text: '"네" "맞아요" "그렇죠" × 10개', options: { breakLine: true, color: C.text3 } },
    { text: '→ 정보 없는데 LLM 호출', options: { color: C.red } },
  ], {
    x: 1.1, y: 2.5, w: 3.4, h: 1.4,
    fontSize: 13, fontFace: FONT_B, lineSpacingMultiple: 1.4, margin: 0,
  });

  // After
  addAccentCard(s5, 5.2, 1.6, 4.0, 2.5, C.accent2);
  s5.addText("AFTER", {
    x: 5.5, y: 1.7, w: 2, h: 0.3,
    fontSize: 10, fontFace: FONT_B, color: C.accent2, bold: true, charSpacing: 2, margin: 0,
  });
  s5.addText("토큰(문자 수) 기준 배치", {
    x: 5.5, y: 2.0, w: 3.4, h: 0.35,
    fontSize: 16, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
  });
  s5.addText([
    { text: '500자 누적 시 LLM 호출', options: { breakLine: true, color: C.text2 } },
    { text: '', options: { breakLine: true, fontSize: 6 } },
    { text: '짧은 발화 10개 ≠ 긴 논증 2개', options: { breakLine: true, color: C.text3 } },
    { text: '→ 실질적 정보량 기준 판단', options: { color: C.accent2 } },
  ], {
    x: 5.5, y: 2.5, w: 3.4, h: 1.4,
    fontSize: 13, fontFace: FONT_B, lineSpacingMultiple: 1.4, margin: 0,
  });

  // Progress bar visualization
  addCard(s5, 0.8, 4.35, 8.4, 0.9);
  s5.addText("UI 프로그레스 바로 상태 투명화", {
    x: 1.1, y: 4.4, w: 5, h: 0.3,
    fontSize: 12, fontFace: FONT_B, color: C.text2, margin: 0,
  });
  // Track
  s5.addShape("rect", { x: 1.1, y: 4.8, w: 5.5, h: 0.15, fill: { color: C.border } });
  // Fill
  s5.addShape("rect", { x: 1.1, y: 4.8, w: 2.7, h: 0.15, fill: { color: C.accent3 } });
  s5.addText("구조화  245 / 500", {
    x: 6.8, y: 4.7, w: 2.2, h: 0.35,
    fontSize: 13, fontFace: FONT_B, color: C.accent3, bold: true, margin: 0,
  });

  addSlideNumber(s5, 5, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 6: Solution 3 — 부동의 기반 자료 수집
  // ════════════════════════════════════════════════════════════
  let s6 = pres.addSlide();
  s6.background = { color: C.bg };

  s6.addText("03", {
    x: 0.8, y: 0.4, w: 1, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent2, bold: true, charSpacing: 3, margin: 0,
  });
  s6.addText("동의 중이면 검색 안 한다", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });
  s6.addText("부동의(의견 대립) 감지 시에만 자료 검색 실행", {
    x: 0.8, y: 1.35, w: 8.4, h: 0.3,
    fontSize: 13, fontFace: FONT_B, color: C.text2, margin: 0,
  });

  // Decision logic
  addCard(s6, 0.8, 1.9, 8.4, 1.3);
  s6.addText("검색 트리거 조건", {
    x: 1.1, y: 2.0, w: 3, h: 0.3,
    fontSize: 12, fontFace: FONT_B, color: C.accent2, bold: true, margin: 0,
  });
  s6.addText([
    { text: 'positions >= 2', options: { fontFace: "Consolas", color: C.accent2, bold: true } },
    { text: '   2명 이상의 서로 다른 입장 존재', options: { color: C.text2 } },
  ], {
    x: 1.1, y: 2.35, w: 7.9, h: 0.3,
    fontSize: 13, fontFace: FONT_B, margin: 0,
  });
  s6.addText([
    { text: 'consensus == null', options: { fontFace: "Consolas", color: C.red, bold: true } },
    { text: '   아직 합의에 도달하지 않음', options: { color: C.text2 } },
  ], {
    x: 1.1, y: 2.7, w: 7.9, h: 0.3,
    fontSize: 13, fontFace: FONT_B, margin: 0,
  });

  // Before/After numbers
  addAccentCard(s6, 0.8, 3.5, 4.0, 1.8, C.red);
  s6.addText("BEFORE", {
    x: 1.1, y: 3.6, w: 2, h: 0.25,
    fontSize: 10, fontFace: FONT_B, color: C.red, bold: true, charSpacing: 2, margin: 0,
  });
  s6.addText([
    { text: 'LLM 엔티티 추출', options: { breakLine: true, color: C.text3 } },
    { text: '180회', options: { breakLine: true, fontSize: 28, bold: true, color: C.red, fontFace: FONT_H } },
    { text: '', options: { breakLine: true, fontSize: 4 } },
    { text: '웹검색  60회  |  중복검색  30회', options: { color: C.text3 } },
  ], {
    x: 1.1, y: 3.9, w: 3.5, h: 1.3,
    fontSize: 12, fontFace: FONT_B, lineSpacingMultiple: 1.2, margin: 0,
  });

  addAccentCard(s6, 5.2, 3.5, 4.0, 1.8, C.accent2);
  s6.addText("AFTER", {
    x: 5.5, y: 3.6, w: 2, h: 0.25,
    fontSize: 10, fontFace: FONT_B, color: C.accent2, bold: true, charSpacing: 2, margin: 0,
  });
  s6.addText([
    { text: 'LLM 엔티티 추출', options: { breakLine: true, color: C.text3 } },
    { text: '30회', options: { breakLine: true, fontSize: 28, bold: true, color: C.accent2, fontFace: FONT_H } },
    { text: '', options: { breakLine: true, fontSize: 4 } },
    { text: '웹검색  15회  |  캐시 히트로 중복 0', options: { color: C.text3 } },
  ], {
    x: 5.5, y: 3.9, w: 3.5, h: 1.3,
    fontSize: 12, fontFace: FONT_B, lineSpacingMultiple: 1.2, margin: 0,
  });

  addSlideNumber(s6, 6, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 7: Doherty Threshold
  // ════════════════════════════════════════════════════════════
  let s7 = pres.addSlide();
  s7.background = { color: C.bg };

  s7.addText("DOHERTY THRESHOLD", {
    x: 0.8, y: 0.4, w: 4, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent, bold: true, charSpacing: 3, margin: 0,
  });
  s7.addText("0.4초 안에 인터랙션", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });
  s7.addText("시스템 응답이 400ms 이내이면 사용자가 즉각적으로 느끼고 생산성이 급격히 향상된다", {
    x: 0.8, y: 1.35, w: 8.4, h: 0.35,
    fontSize: 12, fontFace: FONT_B, color: C.text3, italic: true, margin: 0,
  });

  // Path A (most common)
  addAccentCard(s7, 0.8, 1.9, 5.5, 1.4, C.accent2);
  s7.addText("경로 A  |  일반 발화 (전체의 ~80%)", {
    x: 1.1, y: 2.0, w: 5, h: 0.3,
    fontSize: 11, fontFace: FONT_B, color: C.accent2, bold: true, margin: 0,
  });
  s7.addText([
    { text: 'STT (MLX 가속)', options: { breakLine: true, color: C.text2 } },
    { text: 'DB 저장 + 토픽 Stage1 + 트리거', options: { breakLine: true, color: C.text2 } },
    { text: '쟁점/검색 (토큰 미달 → 스킵)', options: { color: C.text2 } },
  ], {
    x: 1.1, y: 2.35, w: 3.5, h: 0.85,
    fontSize: 12, fontFace: FONT_B, lineSpacingMultiple: 1.3, margin: 0,
  });
  s7.addText([
    { text: '100~300ms', options: { breakLine: true, color: C.text3 } },
    { text: '< 15ms', options: { breakLine: true, color: C.text3 } },
    { text: '0ms', options: { color: C.text3 } },
  ], {
    x: 4.2, y: 2.35, w: 1.8, h: 0.85,
    fontSize: 12, fontFace: FONT_B, lineSpacingMultiple: 1.3, align: "right", margin: 0,
  });

  // Big number
  addCard(s7, 6.6, 1.9, 2.6, 1.4);
  s7.addText("< 0.4s", {
    x: 6.6, y: 2.05, w: 2.6, h: 0.8,
    fontSize: 36, fontFace: FONT_H, color: C.accent2, bold: true, align: "center", margin: 0,
  });
  s7.addText("도어티 임계 충족", {
    x: 6.6, y: 2.8, w: 2.6, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.text3, align: "center", margin: 0,
  });

  // Path C/D (async)
  addAccentCard(s7, 0.8, 3.6, 8.4, 1.2, C.accent3);
  s7.addText("경로 C/D  |  LLM 호출이 필요한 발화 (~20%)", {
    x: 1.1, y: 3.7, w: 6, h: 0.3,
    fontSize: 11, fontFace: FONT_B, color: C.accent3, bold: true, margin: 0,
  });
  s7.addText([
    { text: '비동기 아키텍처: ', options: { bold: true, color: C.white } },
    { text: 'transcript(발화 텍스트)는 STT 완료 즉시 push → ', options: { color: C.text2 } },
    { text: '0.4초 이내', options: { color: C.accent2, bold: true } },
  ], {
    x: 1.1, y: 4.05, w: 7.9, h: 0.3,
    fontSize: 13, fontFace: FONT_B, margin: 0,
  });
  s7.addText("analysis(쟁점/자료)는 백그라운드 Task로 실행 → 완료 시 별도 push", {
    x: 1.1, y: 4.35, w: 7.9, h: 0.3,
    fontSize: 12, fontFace: FONT_B, color: C.text3, margin: 0,
  });

  // Summary
  addCard(s7, 0.8, 5.0, 8.4, 0.45);
  s7.addText("사용자 체감: 모든 발화가 즉시 표시되고, 분석 결과는 점진적으로 갱신", {
    x: 1.1, y: 5.05, w: 7.9, h: 0.35,
    fontSize: 13, fontFace: FONT_B, color: C.accent, valign: "middle", margin: 0,
  });

  addSlideNumber(s7, 7, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 8: 6종 개입 트리거
  // ════════════════════════════════════════════════════════════
  let s8 = pres.addSlide();
  s8.background = { color: C.bg };

  s8.addText("TRIGGERS", {
    x: 0.8, y: 0.4, w: 3, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent3, bold: true, charSpacing: 3, margin: 0,
  });
  s8.addText("6종 개입 트리거", {
    x: 0.8, y: 0.75, w: 5, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });
  s8.addText("전부 LLM 0회  |  키워드 + 패턴 기반  |  판정 < 10ms", {
    x: 5.5, y: 0.85, w: 3.7, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.text3, align: "right", margin: 0,
  });

  const triggers = [
    { name: "consensus", desc: "합의 감지", detail: '"그렇게 하죠", "동의합니다"', level: "INFO", color: C.accent },
    { name: "loop", desc: "논의 교착", detail: "동일 단어 3회+ 반복 감지", level: "WARNING", color: C.accent3 },
    { name: "no_decision", desc: "결정 없이 넘어감", detail: "토픽 전환 시 이전 결정 없음", level: "WARNING", color: C.accent3 },
    { name: "info_needed", desc: "정보 필요", detail: '"확인해봐야", "자료가 있나"', level: "INFO", color: C.accent },
    { name: "silence", desc: "진행 멈춤", detail: "5초 이상 침묵 감지", level: "INFO", color: C.accent },
    { name: "time_over", desc: "시간 초과", detail: "안건 10분 경과 경고", level: "WARNING", color: C.accent3 },
  ];

  triggers.forEach((t, i) => {
    const row = Math.floor(i / 2);
    const col = i % 2;
    const cx = 0.8 + col * 4.4;
    const cy = 1.5 + row * 1.25;
    addAccentCard(s8, cx, cy, 4.0, 1.05, t.color);
    s8.addText(t.name, {
      x: cx + 0.25, y: cy + 0.08, w: 2.5, h: 0.25,
      fontSize: 10, fontFace: "Consolas", color: t.color, bold: true, margin: 0,
    });
    s8.addText(t.level, {
      x: cx + 2.8, y: cy + 0.08, w: 0.9, h: 0.25,
      fontSize: 9, fontFace: FONT_B, color: C.text3, align: "right", margin: 0,
    });
    s8.addText(t.desc, {
      x: cx + 0.25, y: cy + 0.35, w: 3.5, h: 0.3,
      fontSize: 14, fontFace: FONT_B, color: C.white, bold: true, margin: 0,
    });
    s8.addText(t.detail, {
      x: cx + 0.25, y: cy + 0.65, w: 3.5, h: 0.3,
      fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
    });
  });

  // Bottom note
  addCard(s8, 0.8, 5.05, 8.4, 0.4);
  s8.addText("회의 진행의 역학(교착, 합의, 전환, 시간 초과)을 LLM 없이 모델링 → 도어티 임계 충족", {
    x: 1.1, y: 5.08, w: 7.9, h: 0.35,
    fontSize: 12, fontFace: FONT_B, color: C.text2, valign: "middle", margin: 0,
  });

  addSlideNumber(s8, 8, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 9: Architecture
  // ════════════════════════════════════════════════════════════
  let s9 = pres.addSlide();
  s9.background = { color: C.bg };

  s9.addText("ARCHITECTURE", {
    x: 0.8, y: 0.4, w: 3, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent, bold: true, charSpacing: 3, margin: 0,
  });
  s9.addText("실시간 분석 파이프라인", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });

  // Pipeline flow — horizontal blocks
  const pipe = [
    { label: "마이크", sub: "WebSocket", color: C.text3, x: 0.3, w: 1.2 },
    { label: "VAD", sub: "적응형 RMS", color: C.text3, x: 1.7, w: 1.2 },
    { label: "STT", sub: "mlx-whisper", color: C.accent, x: 3.1, w: 1.4 },
    { label: "화자 식별", sub: "sherpa-onnx", color: C.accent, x: 4.7, w: 1.4 },
  ];
  pipe.forEach(p => {
    s9.addShape("rect", {
      x: p.x, y: 1.55, w: p.w, h: 0.85,
      fill: { color: C.bgCard },
    });
    s9.addShape("rect", {
      x: p.x, y: 1.55, w: p.w, h: 0.04,
      fill: { color: p.color },
    });
    s9.addText(p.label, {
      x: p.x, y: 1.65, w: p.w, h: 0.35,
      fontSize: 12, fontFace: FONT_B, color: C.white, bold: true, align: "center", margin: 0,
    });
    s9.addText(p.sub, {
      x: p.x, y: 1.95, w: p.w, h: 0.3,
      fontSize: 10, fontFace: FONT_B, color: C.text3, align: "center", margin: 0,
    });
  });

  // Arrow to pipeline
  s9.addText("on_utterance()", {
    x: 6.3, y: 1.65, w: 1.7, h: 0.7,
    fontSize: 11, fontFace: "Consolas", color: C.accent, valign: "middle", align: "center", margin: 0,
  });
  s9.addShape("rect", {
    x: 6.3, y: 1.55, w: 1.7, h: 0.85,
    fill: { color: C.bgCard },
  });
  s9.addShape("rect", {
    x: 6.3, y: 1.55, w: 1.7, h: 0.04,
    fill: { color: C.accent2 },
  });
  s9.addText("Pipeline", {
    x: 6.3, y: 1.62, w: 1.7, h: 0.35,
    fontSize: 12, fontFace: FONT_B, color: C.white, bold: true, align: "center", margin: 0,
  });
  s9.addText("on_utterance()", {
    x: 6.3, y: 1.95, w: 1.7, h: 0.3,
    fontSize: 9, fontFace: "Consolas", color: C.accent2, align: "center", margin: 0,
  });

  // WS push
  s9.addShape("rect", {
    x: 8.2, y: 1.55, w: 1.5, h: 0.85,
    fill: { color: C.bgCard },
  });
  s9.addShape("rect", {
    x: 8.2, y: 1.55, w: 1.5, h: 0.04,
    fill: { color: C.accent3 },
  });
  s9.addText("WebSocket", {
    x: 8.2, y: 1.62, w: 1.5, h: 0.35,
    fontSize: 12, fontFace: FONT_B, color: C.white, bold: true, align: "center", margin: 0,
  });
  s9.addText("실시간 push", {
    x: 8.2, y: 1.95, w: 1.5, h: 0.3,
    fontSize: 10, fontFace: FONT_B, color: C.accent3, align: "center", margin: 0,
  });

  // Analysis modules (below pipeline)
  const modules = [
    { label: "토픽 감지", sub: "3단계 필터", note: "LLM ~5%", color: C.accent, x: 0.8, w: 2.5 },
    { label: "트리거 감지", sub: "6종 키워드", note: "LLM 0%", color: C.accent3, x: 3.55, w: 2.5 },
    { label: "쟁점 구조화", sub: "토큰 배치", note: "LLM 조건부", color: C.accent2, x: 6.3, w: 2.5 },
  ];
  modules.forEach(m => {
    s9.addShape("rect", {
      x: m.x, y: 2.8, w: m.w, h: 1.0,
      fill: { color: C.bgCard },
    });
    s9.addShape("rect", {
      x: m.x, y: 2.8, w: 0.05, h: 1.0,
      fill: { color: m.color },
    });
    s9.addText(m.label, {
      x: m.x + 0.2, y: 2.85, w: m.w - 0.3, h: 0.3,
      fontSize: 13, fontFace: FONT_B, color: C.white, bold: true, margin: 0,
    });
    s9.addText(m.sub, {
      x: m.x + 0.2, y: 3.15, w: m.w - 0.3, h: 0.25,
      fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
    });
    s9.addText(m.note, {
      x: m.x + 0.2, y: 3.45, w: m.w - 0.3, h: 0.25,
      fontSize: 10, fontFace: FONT_B, color: m.color, margin: 0,
    });
  });

  // Conditional search
  s9.addShape("rect", {
    x: 0.8, y: 4.1, w: 8.0, h: 0.9,
    fill: { color: C.bgCard },
  });
  s9.addShape("rect", {
    x: 0.8, y: 4.1, w: 0.05, h: 0.9,
    fill: { color: C.red },
  });
  s9.addText("자료 수집 (조건부)", {
    x: 1.1, y: 4.15, w: 3, h: 0.3,
    fontSize: 13, fontFace: FONT_B, color: C.white, bold: true, margin: 0,
  });
  s9.addText("부동의 감지 시에만 실행  |  엔티티 추출 + 사내DB(ChromaDB) + 웹검색(Tavily)  |  쿼리 캐싱", {
    x: 1.1, y: 4.5, w: 7.5, h: 0.3,
    fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
  });

  // Tech stack
  s9.addText("FastAPI + WebSocket  |  SQLite(aiosqlite)  |  MLX + ONNX  |  모두 로컬 실행", {
    x: 0.8, y: 5.15, w: 8.4, h: 0.3,
    fontSize: 11, fontFace: FONT_B, color: C.text3, margin: 0,
  });

  addSlideNumber(s9, 9, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 10: Results — Before/After
  // ════════════════════════════════════════════════════════════
  let s10 = pres.addSlide();
  s10.background = { color: C.bg };

  s10.addText("RESULTS", {
    x: 0.8, y: 0.4, w: 2, h: 0.35,
    fontSize: 11, fontFace: FONT_B, color: C.accent2, bold: true, charSpacing: 3, margin: 0,
  });
  s10.addText("최적화 결과", {
    x: 0.8, y: 0.75, w: 8.4, h: 0.6,
    fontSize: 28, fontFace: FONT_H, color: C.white, margin: 0,
  });
  s10.addText("30분 회의 (180발화) 기준", {
    x: 0.8, y: 1.35, w: 8.4, h: 0.3,
    fontSize: 13, fontFace: FONT_B, color: C.text3, margin: 0,
  });

  // Metric cards — 3 big numbers
  const metrics = [
    { label: "LLM 호출", before: "~250회", after: "~50회", pct: "80%", pctLabel: "감소", color: C.accent },
    { label: "웹검색", before: "~60회", after: "~15회", pct: "75%", pctLabel: "감소", color: C.accent3 },
    { label: "발화당 지연", before: "~2.5s", after: "~0.15s", pct: "94%", pctLabel: "감소", color: C.accent2 },
  ];

  metrics.forEach((m, i) => {
    const cx = 0.8 + i * 3.0;
    addCard(s10, cx, 1.85, 2.7, 2.6);
    s10.addText(m.label, {
      x: cx, y: 1.95, w: 2.7, h: 0.3,
      fontSize: 12, fontFace: FONT_B, color: C.text3, align: "center", margin: 0,
    });
    s10.addText(m.pct, {
      x: cx, y: 2.3, w: 2.7, h: 0.8,
      fontSize: 44, fontFace: FONT_H, color: m.color, bold: true, align: "center", margin: 0,
    });
    s10.addText(m.pctLabel, {
      x: cx, y: 3.05, w: 2.7, h: 0.3,
      fontSize: 14, fontFace: FONT_B, color: m.color, align: "center", margin: 0,
    });
    s10.addText(`${m.before}  →  ${m.after}`, {
      x: cx, y: 3.4, w: 2.7, h: 0.3,
      fontSize: 11, fontFace: FONT_B, color: C.text3, align: "center", margin: 0,
    });
  });

  // Key insight
  addCard(s10, 0.8, 4.7, 8.4, 0.7);
  s10.addText([
    { text: '핵심: ', options: { bold: true, color: C.white } },
    { text: '"LLM을 안 쓰는 판단"으로 80%+ 발화에서 LLM 호출을 제거하고,\n', options: { color: C.text2 } },
    { text: '비동기 아키텍처로 나머지 20%에서도 사용자 체감 지연을 0.4초 이내로 유지', options: { color: C.accent } },
  ], {
    x: 1.1, y: 4.75, w: 7.9, h: 0.6,
    fontSize: 13, fontFace: FONT_B, lineSpacingMultiple: 1.3, valign: "middle", margin: 0,
  });

  addSlideNumber(s10, 10, TOTAL);

  // ════════════════════════════════════════════════════════════
  // SLIDE 11: Closing
  // ════════════════════════════════════════════════════════════
  let s11 = pres.addSlide();
  s11.background = { color: C.bg };

  s11.addShape("rect", { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.accent } });

  s11.addText("MeetingMind", {
    x: 0.8, y: 1.5, w: 8.4, h: 0.8,
    fontSize: 40, fontFace: FONT_H, color: C.white, bold: true, margin: 0,
  });
  s11.addText("언제 생각할지를 판단하는 회의 AI", {
    x: 0.8, y: 2.3, w: 8.4, h: 0.5,
    fontSize: 20, fontFace: FONT_B, color: C.accent, margin: 0,
  });

  // 3 takeaways
  const takeaways = [
    { num: "01", text: "LLM을 안 쓰는 판단이 핵심 설계" },
    { num: "02", text: "회의의 역학을 코드로 모델링" },
    { num: "03", text: "0.4초 도어티 임계 달성" },
  ];
  takeaways.forEach((t, i) => {
    const cy = 3.2 + i * 0.5;
    s11.addText(t.num, {
      x: 0.8, y: cy, w: 0.6, h: 0.4,
      fontSize: 14, fontFace: FONT_H, color: C.accent, bold: true, margin: 0,
    });
    s11.addText(t.text, {
      x: 1.5, y: cy, w: 7, h: 0.4,
      fontSize: 16, fontFace: FONT_B, color: C.text2, margin: 0,
    });
  });

  s11.addText("Q & A", {
    x: 0.8, y: 4.8, w: 8.4, h: 0.5,
    fontSize: 18, fontFace: FONT_B, color: C.text3, margin: 0,
  });

  addSlideNumber(s11, 11, TOTAL);

  // ── Write file ──
  await pres.writeFile({ fileName: "/Users/edwin/Documents/MeetingMind/MeetingMind_발표.pptx" });
  console.log("DONE: MeetingMind_발표.pptx");
}

main().catch(err => { console.error(err); process.exit(1); });
