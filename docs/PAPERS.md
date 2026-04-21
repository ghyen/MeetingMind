# Meeting AI 관련 논문 모음

MeetingMind 최적화를 위한 논문 리서치. 총 53편, 카테고리별 정리.

---

## 1. STT / ASR 기반 모델

### Whisper — Robust Speech Recognition via Large-Scale Weak Supervision
- **Radford et al. (OpenAI), 2023 (ICML)**
- 680k시간 멀티링구얼 데이터로 학습한 encoder-decoder transformer. 파인튜닝 없이 범용 ASR 달성.
- **인사이트**: MeetingMind의 `faster-whisper` 백엔드 기반 모델. 언어 토큰 컨디셔닝을 활용한 한국어 도메인 파인튜닝 가능.
- https://arxiv.org/abs/2212.04356

### Conformer — Convolution-augmented Transformer for Speech Recognition
- **Gulati et al. (Google), 2020 (Interspeech)**
- Self-attention(전역 문맥) + depthwise separable convolution(로컬 피처)를 결합한 macaron 구조. LibriSpeech WER 2.1%/4.3%.
- **인사이트**: sherpa-onnx 스트리밍 트랜스듀서의 인코더 아키텍처. FastConformer 변형으로 추가 속도 개선 가능.
- https://arxiv.org/abs/2005.08100

---

## 2. 스트리밍 / 실시간 ASR & 레이턴시 최적화

### Simul-Whisper — Attention-Guided Streaming Whisper with Truncation Detection
- **Wang et al., 2024 (Interspeech)**
- 파인튜닝 없이 Whisper를 스트리밍 모델로 변환. Cross-attention 정렬로 청크 기반 디코딩, 1초 청크에서 WER 저하 1.46%p만.
- **인사이트**: 현재 silence detection 기반 청크 처리를 진정한 스트리밍 디코딩으로 대체 가능. 체감 레이턴시 수초 → ~1초.
- https://arxiv.org/abs/2406.10052

### Stateful FastConformer with Cache-based Inference for Streaming ASR
- **Noroozi et al. (NVIDIA), 2024 (ICASSP)**
- Look-ahead 컨텍스트 제한 + 활성화 캐싱으로 비자기회귀 인코더를 자기회귀적으로 추론. 버퍼 스트리밍 대비 3배 효율.
- **인사이트**: sherpa-onnx 트랜스듀서와 동일 아키텍처 패턴. 전용 스트리밍 모델 전환 시 강력한 후보.
- https://arxiv.org/pdf/2312.17279

### Distil-Whisper — Robust Knowledge Distillation via Large-Scale Pseudo Labelling
- **Gandhi et al. (Hugging Face), 2023**
- Whisper를 51% 작고 5.8배 빠르게 증류, WER 1% 이내. Speculative decoding으로 원본과 수학적으로 동일한 출력에서 2배 속도업. 긴 오디오 환각 감소.
- **인사이트**: `faster-whisper` 백엔드에 drop-in 대체 가능. CPU에서 레이턴시/메모리 대폭 절감. 긴 회의에서 환각 감소 효과.
- https://arxiv.org/abs/2311.00430

### RNN-Transducer (RNN-T)
- **Graves (U of Toronto), 2012**
- 인코더 + 예측 네트워크 + joint 네트워크 결합. 현재 프레임과 이전 레이블에만 의존하므로 스트리밍에 자연적으로 적합.
- **인사이트**: sherpa-onnx `OnlineRecognizer.from_transducer()`의 기반 아키텍처. 엔드포인트 감지 파라미터 튜닝의 이론적 근거.
- https://arxiv.org/abs/1211.3711

### Speech ReaLLM — Real-time Streaming Speech Recognition with Multimodal LLMs
- **Seide et al., 2024**
- 첫 decoder-only 스트리밍 ASR. 명시적 엔드포인트 없이 연속 오디오 스트림 처리. Decoder-only ASR + RNN-T 결합.
- **인사이트**: ASR과 NLU를 단일 모델로 통합하는 미래 방향. 별도 STT→LLM 파이프라인 제거 가능.
- https://arxiv.org/abs/2406.09569

---

## 3. 화자 분리 (Speaker Diarization)

### pyannote.audio 2.1 Speaker Diarization Pipeline
- **Bredin & Laurent, 2023 (Interspeech)**
- 3단계: (1) 슬라이딩 윈도우 세그멘테이션, (2) 화자 임베딩 추출, (3) 병합 클러스터링. Powerset 학습으로 겹침 발화 감지.
- **인사이트**: 현재 `SpeakerIdentifier`보다 겹침 발화 처리가 우수. 교차 대화가 잦은 회의에서 파이프라인 대체/보강 가능.
- https://www.isca-archive.org/interspeech_2023/bredin23_interspeech.html

### EEND — End-to-End Neural Speaker Diarization with Self-Attention
- **Fujita et al. (Hitachi), 2019**
- 화자 분리를 멀티레이블 프레임 분류로 재정의. Self-attention으로 겹침 발화를 자연스럽게 처리.
- **인사이트**: 현재 시스템은 발화 단위 화자 식별로 겹침 발화를 놓침. EEND를 병렬 실행하면 프레임 레벨 화자 레이블 제공 가능.
- https://arxiv.org/abs/1909.06247

### 3D-Speaker Toolkit — Multimodal Speaker Verification and Diarization
- **Chen et al. (Alibaba DAMO), 2024**
- 음향/시맨틱/시각 모듈 통합. ERes2NetV2 아키텍처, 10k+ 화자 데이터셋.
- **인사이트**: 현재 사용 중인 3dspeaker 임베딩 모델의 기반 논문. 회의 환경 특화 파인튜닝 참고용.
- https://arxiv.org/abs/2403.19971

### Once More Diarization — Segment-Level Speaker Reassignment
- **Meeus et al., 2024**
- 초기 분리 후 세그먼트 단위 화자 재할당으로 화자 혼동 오류 40%+ 교정.
- **인사이트**: 회의 종료 후 `SpeakerIdentifier` 결과를 전체적으로 재검토하여 오할당 교정. 특히 짧은 발화의 `_fallback_label` 개선.
- https://arxiv.org/abs/2406.03155

### DiarizationLM — Speaker Diarization Post-Processing with LLMs
- **Quan Wang et al. (Google), 2024**
- LLM으로 화자 분리 결과 후처리. Fisher에서 단어 분리 오류율 55.5% 감소, Callhome에서 44.9% 감소.
- **인사이트**: 기존 분리 파이프라인 뒤에 LLM 후처리 단계 추가로 화자 귀속 정확도 대폭 개선. 언어적 문맥 활용.
- https://arxiv.org/abs/2401.03506

### Interactive Real-Time Speaker Diarization Correction with Human Feedback
- **Yuning Wu et al., 2025**
- 사용자의 구두 피드백으로 실시간 분리 오류 교정. AMI 테스트셋에서 DER 9.92% 감소, 화자 혼동 오류 44.23% 감소.
- **인사이트**: "그건 사실 김 팀장이 말한 겁니다" 같은 구두 교정으로 실시간 분리 모델 업데이트. Human-in-the-loop.
- https://arxiv.org/abs/2509.18377

---

## 4. 다중 화자 / 겹침 발화 처리

### Speaker-Aware CTC (SACTC) — Disentangling Speakers in Multi-Talker Speech Recognition
- **Wang et al., 2024 (ICASSP 2025)**
- CTC 변형으로 다른 화자의 토큰을 구분된 시간 위치에 배치. 겹침 발화 WER 15% 감소.
- **인사이트**: 동시 발화가 잦은 회의에서 단일 화자 트랜스듀서 대체. 겹침 발화가 한 화자로 병합되는 문제 해결.
- https://arxiv.org/abs/2409.12388

### Meeting Recognition with Continuous Speech Separation and Transcription-Supported Diarization
- **Boeddeker et al., 2024**
- TF-GridNet으로 연속 음성 분리 후 화자 무관 ASR. ASR 문장/단어 경계로 화자 전환 감지 개선.
- **인사이트**: ASR 출력을 화자 할당 결정에 피드백. 빠른 화자 교대 시 정확도 향상.
- https://arxiv.org/abs/2309.16482

---

## 5. ASR 오류 교정 / 후처리

### ASR Error Correction using Large Language Models
- **Radhakrishnan et al., 2024**
- LLM으로 ASR 오류 교정: N-best 리스트 리랭킹 + 제약 디코딩. ASR 래티스 기반 제약으로 LLM 환각 방지.
- **인사이트**: STT 결과를 LLM 요약 전에 교정 단계 추가. 도메인 전문 용어 오인식 대폭 감소. TODO #13과 직접 연관.
- https://arxiv.org/abs/2409.09554

### Evolutionary Prompt Design for LLM-Based Post-ASR Error Correction
- **Biswas et al., 2024**
- 진화 알고리즘으로 ASR 교정 프롬프트 자동 최적화. 수작업 프롬프트보다 유의미하게 우수한 성능.
- **인사이트**: TODO #13의 교정 프롬프트를 자동으로 최적화하는 방법. 한국어 회의 오류 패턴에 특화된 프롬프트 탐색 가능.
- https://arxiv.org/abs/2407.16370

---

## 6. 도메인 적응 (Domain Adaptation)

### STAR — Self-Taught Recognizer: Unsupervised Adaptation for Speech Foundation Models
- **Hu et al. (NVIDIA), 2024 (NeurIPS)**
- 비지도 적응 프레임워크: 라벨 없는 타겟 도메인 오디오만으로 Whisper 적응. 14개 도메인 평균 상대 WER 13.5% 감소.
- **인사이트**: 수동 전사 없이 특정 회의 환경(회사 전문 용어, 회의실 음향)에 Whisper 적응 가능. 가장 실용적인 도메인 적응 방법.
- https://arxiv.org/abs/2405.14161

### Whisper-AT — Noise-Robust ASR Models are Also Strong Audio Event Taggers
- **Gong et al. (MIT/IBM), 2023 (Interspeech)**
- Whisper 내부 표현이 배경 오디오 이벤트 정보를 풍부하게 인코딩함을 발견. 1% 미만 추가 연산으로 527 클래스 오디오 태깅.
- **인사이트**: 회의 관련 이벤트 감지(타이핑, 웃음, 문 닫힘) 가능. 회의록 보강("14:23에 회의 중단") 또는 VAD 필터 개선.
- https://arxiv.org/abs/2307.03183

---

## 7. 회의 요약 (Meeting Summarization)

### Abstractive Meeting Summarization: A Survey
- **Rennard et al., 2023 (TACL)**
- 추상적 회의 요약의 도전 과제, 데이터셋(AMI, ICSI, QMSum), 모델, 평가 메트릭 종합 서베이.
- **인사이트**: 요약 아키텍처 선택의 로드맵. 긴 입력, 다중 화자, 담화 구조 등 도전 과제가 시스템 설계 결정에 직접 매핑.
- https://arxiv.org/abs/2208.04163

### HMNet — Hierarchical Network for Abstractive Meeting Summarization
- **Zhu et al. (Microsoft Research), 2020 (EMNLP)**
- 2단계 계층적 트랜스포머: 발화별 단어 인코더 → 턴 레벨 인코더 + 화자 역할 임베딩. 크로스 도메인 사전학습으로 ROUGE-1 ~4점 향상.
- **인사이트**: 발화가 순차적으로 도착하는 스트리밍 입력에 자연스럽게 매핑. 화자 역할 임베딩은 다중 참여자 회의에 유용.
- https://arxiv.org/abs/2004.02016

### QMSum — Query-based Multi-domain Meeting Summarization
- **Zhong et al., 2021 (NAACL)**
- 쿼리 기반 회의 요약: 관련 구간 위치 파악 후 요약. 3개 도메인 232회의에서 1,808 쿼리-요약 쌍.
- **인사이트**: "예산 결정 사항이 뭐였지?" 같은 타겟 질문 지원. locate-then-summarize 패턴은 실시간 온디맨드 쿼리에 적합.
- https://arxiv.org/abs/2104.05938

### DialogLM — Pre-trained Model for Long Dialogue Understanding and Summarization
- **Zhong et al., 2022 (AAAI)**
- 대화 특화 노이즈(화자 마스킹, 턴 분할/병합/순열)로 사전학습. 하이브리드 sparse+dense attention으로 8,000+ 토큰 처리.
- **인사이트**: 대화 인식 사전학습과 긴 문맥 처리가 결합된 강력한 백본. 긴 다중 화자 회의록 처리에 적합.
- https://arxiv.org/abs/2109.02492

### Dialogue Summarization with Mixture of Experts based on LLMs
- **Feng et al., 2024 (ACL)**
- 여러 LLM을 전문 "expert"로 사용, 역할 기반 라우팅 + 융합 모듈. 단일 LLM 대비 다양한 측면 커버.
- **인사이트**: 액션 아이템, 결정 사항, 일반 논의를 전문 모델로 라우팅하여 요약 커버리지 향상.
- https://aclanthology.org/2024.acl-long.385/

### Summaries, Highlights, and Action Items — LLM-powered Meeting Recap System
- **Asthana et al. (Microsoft), 2023 (CSCW 2024)**
- 인지과학 기반 이중 형식: "주요 하이라이트"(빠른 스캔용) + "구조화된 계층 회의록"(상세 리뷰용). 실제 Microsoft 업무 회의로 평가.
- **인사이트**: 회의 AI 출력 UX 설계 검증. 이중 형식(하이라이트 + 구조화 회의록)을 출력 모드로 직접 구현 가능.
- https://arxiv.org/abs/2307.15793

---

## 8. 토픽 분할 (Topic Segmentation)

### Unsupervised Topic Segmentation of Meetings with BERT Embeddings
- **Solbiati et al., 2021**
- BERT 문장 임베딩으로 비지도 토픽 분할. AMI/ICSI에서 기존 비지도 방법 대비 15.5% 오류율 감소.
- **인사이트**: 라벨 없이 도메인 무관하게 작동하는 제로샷 토픽 경계 감지기. 스트리밍 회의록에 직접 적용 가능.
- https://arxiv.org/abs/2106.12978

### M3Seg — Maximum-Minimum Mutual Information for Unsupervised Topic Segmentation
- **Wang et al., 2023 (EMNLP)**
- 2단계 비지도: (1) 전역-로컬 상호 정보 최대화로 세그먼트 인코딩 학습, (2) 인접 세그먼트 간 상호 정보 최소화로 경계 감지. 기존 SOTA 대비 18-37% 개선.
- **인사이트**: 원리적 경계 감지 프레임워크. 슬라이딩 윈도우 적용으로 스트리밍 처리 가능.
- https://aclanthology.org/2023.emnlp-main.492/

### Improving Long Document Topic Segmentation with Enhanced Coherence Modeling
- **Yu et al., 2023 (EMNLP)**
- TSSP(Topic-aware Sentence Structure Prediction) + CSSL(Contrastive Semantic Similarity Learning). Longformer로 F1 3.42점 향상.
- **인사이트**: 일관성 모델링 기법을 회의 분할 파이프라인에 통합하여 의미적으로 더 일관된 토픽 블록 생성.
- https://arxiv.org/abs/2310.11772

---

## 9. 액션 아이템 추출

### Meeting Action Item Detection with Regularized Context Modeling
- **Liu et al., 2023 (ICASSP)**
- Context-Drop: 대조 학습으로 로컬/글로벌 문맥 활용. 최초/최대 규모 중국어 회의 액션 아이템 코퍼스 공개.
- **인사이트**: 실시간 처리에서 최근 발화(로컬)와 회의 전체(글로벌) 문맥 모두 활용 가능. 한국어/중국어 회의에 관련성 높음.
- https://arxiv.org/abs/2303.16763

### Action-Item-Driven Summarization of Long Meeting Transcripts
- **Golia & Kalita, 2023**
- 토픽 분할 → 섹션별 액션 아이템 추출 → 액션 아이템 중심 재귀 요약. BERTScore 64.98 (BART 대비 ~5% 향상).
- **인사이트**: 토픽 세그먼트 완료 시마다 증분적으로 액션 아이템 추출 + 실행 중심 요약 유지 가능.
- https://arxiv.org/abs/2312.17581

---

## 10. 논쟁/합의 감지 (Argument Mining & Stance Detection)

### Agree to Disagree — Improving Disagreement Detection with Dual GRUs
- **Yin et al., 2017**
- Siamese 듀얼 GRU로 동의/비동의 감지. 수작업 피처 없이 ABCD 데이터셋에서 F1 0.804.
- **인사이트**: 회의 참여자의 동의/반대 자동 추적. "이견 영역" 섹션 자동 생성에 활용.
- https://arxiv.org/abs/1708.05582

### Detecting Agreement in Multi-party Dialogue
- **Addlesee et al., 2023**
- 화자 분리 기반 vs 빈도-근접 기반 절차적 방법 비교. 절차적 방법(0.44)이 분리 기반(0.28)보다 우수.
- **인사이트**: 실시간 합의 감지에서 단순한 절차적 방법이 더 효과적일 수 있음. 실용적 하이브리드 접근 제시.
- https://arxiv.org/abs/2311.03021

### CFAS — Consensus-Focused Abstractive Meeting Summarization
- **2025**
- 3단계: 토픽 분할 → 합의 식별(참여자 동의/결정 감지) → 합의 인식 요약.
- **인사이트**: 합의 식별 모듈을 스트리밍 토픽 분할기와 함께 실행하여 실시간 결정 사항 플래그. 요약에 "논의된 것"이 아닌 "결정된 것" 강조.
- https://link.springer.com/article/10.1007/s44443-025-00210-3

---

## 11. 실시간 회의 분석

### Policies and Evaluation for Online Meeting Summarization
- **Schneider, Turchi (Zoom) & Waibel (KIT), 2025**
- 최초의 체계적 온라인(스트리밍) 회의 요약 연구. 입력 토큰 소비 vs 출력 토큰 생성의 read/write 정책 제안. 적응형 정책이 고정 스케줄보다 우수.
- **인사이트**: 실시간 요약의 핵심 문제 "언제, 어떻게 부분 요약을 생성할 것인가"에 대한 직접적 해답. 적응형 정책과 레이턴시 메트릭 즉시 활용 가능.
- https://arxiv.org/abs/2502.03111

### Dynamic Agenda-Aware Real-Time Meeting Summarization
- **2025**
- 동적 안건 인식 실시간 요약: 진화하는 안건에 따라 증분 요약 생성. LLM + 안건 컨텍스트 가이드.
- **인사이트**: 회의 안건이 있으면 이를 기준으로 실시간 요약 앵커링. 안건 진행 상황 추적 구조화된 출력.
- https://link.springer.com/article/10.1007/s44443-025-00304-y

### Real-time Decision Detection in Multi-party Dialogue
- **Frampton et al., 2009 (EMNLP)**
- 의사결정 하위 대화 실시간 감지. 발화 역할 모델링: 이슈 제기 → 제안 → 수락/거절.
- **인사이트**: 이슈→제안→수락 구조를 FSM으로 구현하여 실시간 의사결정 감지. MeetingMind의 쟁점 구조화와 직접 연관.
- https://aclanthology.org/D09-1118/

---

## 12. 대화 행위 분류 (Dialogue Act Classification)

### What Helps Transformers Recognize Conversational Structure?
- **Zelasko et al., 2021 (TACL)**
- XLNet/Longformer로 대화 행위 분류. 3가지 핵심 요인: (1) 대화 문맥, (2) 구두점 영향 매우 큼, (3) 레이블 세분화는 영향 없음.
- **인사이트**: ASR 출력에 구두점 복원 단계 추가가 중요. 충분한 대화 문맥 제공 필요. MRDA 결과가 회의록에 직접 관련.
- https://arxiv.org/abs/2107.02294

### ICSI MRDA Corpus
- **Shriberg et al., 2004**
- 75개 ICSI 회의, 72시간 분량, 180,000+ 수작업 대화 행위 태그. 진술, 질문, 백채널, 중단 등 DA 분류 체계 정의.
- **인사이트**: 회의 대화 행위 분류의 표준 학습 데이터/분류 체계. 실시간 질문/제안/약속 식별에 활용.
- https://aclanthology.org/W04-2319/

---

## 13. 회의록 / 벤치마크

### ICASSP 2023 MUG Challenge (AliMeeting4MUG)
- **Zhang et al., 2023 (ICASSP)**
- 5개 트랙: 토픽 분할, 추출 요약(토픽/세션), 토픽 제목 생성, 키프레이즈 추출, 액션 아이템 감지. 최대 규모 회의 코퍼스 공개.
- **인사이트**: 자동 회의록 생성에 필요한 5대 컴포넌트의 멀티태스크 벤치마크. 학습/평가 데이터로 활용 가능.
- https://arxiv.org/abs/2303.13932

---

## 14. RAG & 정보 검색

### RAGate — Adaptive Retrieval-Augmented Generation for Conversational Systems
- **Xi Wang et al., 2024**
- 게이팅 메커니즘으로 대화 턴별 RAG 필요 여부를 동적 예측. 불필요한 검색을 건너뛰어 품질과 신뢰도 동시 향상.
- **인사이트**: 모든 발화에 ChromaDB 검색을 트리거하지 않고, 실제로 외부 지식이 필요한 발화만 선별. 불필요한 레이턴시 제거.
- https://arxiv.org/abs/2407.21712

### Agentic RAG Survey
- **Aditi Singh et al., 2025**
- 나이브 RAG에서 에이전틱 RAG로의 진화. 플래너/서처/리즈너 에이전트를 오케스트레이터가 조율.
- **인사이트**: 과거 회의록, 사내 문서, 웹 결과 등 어떤 소스를 검색할지 자율 결정하는 멀티 에이전트 파이프라인.
- https://arxiv.org/abs/2501.09136

### FAVA — Fine-grained Hallucination Detection and Editing
- **Abhika Mishra et al., 2024 (COLM)**
- 환각 유형 분류(엔티티 오류, 관계 오류, 검증 불가 진술) + 스팬 레벨 감지/교정. ChatGPT/GPT-4보다 우수.
- **인사이트**: 회의 중 언급된 사실 실시간 검증. LLM 요약의 환각 방지.
- https://arxiv.org/abs/2401.06855

### Contrastive Learning to Improve Retrieval for Real-world Fact Checking (CFR)
- **Hartman et al., 2024**
- 대조 학습 기반 사실 확인 리랭커. 복잡한 실제 주장에 대한 증거 검색 품질 향상.
- **인사이트**: 회의 참여자의 사실 주장에 대해 검증 증거 검색 품질 개선. RAG 파이프라인 보강.
- https://arxiv.org/abs/2410.04657

---

## 15. LLM 추론 최적화

### Speculative Streaming — Fast LLM Inference without Auxiliary Models
- **Bhendawade et al., 2024**
- 드래프트 모델을 타겟 모델에 융합. 파인튜닝 목적을 next-token → future n-gram 예측으로 변경. 보조 모델 없이 1.8-3.1배 속도업.
- **인사이트**: 회의 요약, 액션 아이템, 실시간 Q&A 생성 레이턴시 대폭 감소. 단일 모델 배포로 간소화.
- https://arxiv.org/abs/2402.11131

### StreamingLLM — Efficient Streaming Language Models with Attention Sinks
- **Guangxuan Xiao et al., 2023 (ICLR 2024)**
- LLM이 초기 토큰에 과도한 attention 할당하는 "attention sinks" 발견. 초기 토큰 KV 상태를 슬라이딩 윈도우에 보존하면 무한 길이 스트림 처리 가능. 슬라이딩 윈도우 재계산 대비 22.2배 속도업.
- **인사이트**: 컨텍스트 윈도우 초과하는 긴 회의록 처리에 직접 적용. 수시간 회의에서도 메모리 오버플로 없이 연속 LLM 문맥 유지.
- https://arxiv.org/abs/2309.17453

### vLLM — Efficient Memory Management with PagedAttention
- **Woosuk Kwon et al., 2023 (SOSP)**
- OS 가상 메모리 페이징에서 영감받은 KV 캐시 관리. 메모리 단편화 제거, 요청 간 KV 캐시 공유. 처리량 2-4배 향상.
- **인사이트**: 다중 동시 회의 세션 서빙 시 효율적 배칭. 요청당 레이턴시 유지하면서 처리량 증가.
- https://arxiv.org/abs/2309.06180

---

## 16. 실시간 대화 시스템 & 풀듀플렉스

### Moshi — A Speech-Text Foundation Model for Real-Time Dialogue
- **Defossez et al. (Kyutai), 2024**
- 최초의 실시간 풀듀플렉스 음성 LLM. 이론 160ms / 실제 200ms 레이턴시. "Inner Monologue"로 텍스트→오디오 병렬 예측. 겹침 발화 네이티브 처리.
- **인사이트**: 실시간 회의 AI의 gold standard. 음성 이해, 응답 생성, 인터럽션 처리를 동시에 sub-200ms로 달성.
- https://arxiv.org/abs/2410.00037

### Beyond the Turn-Based Game — Duplex Models with TDM
- **Xinrong Zhang et al., 2024**
- 시분할 다중화(TDM) 인코딩-디코딩. 메시지를 타임슬라이스로 분할, 증분 처리, 새 입력 시 즉시 생성 중단.
- **인사이트**: 화자가 말을 끝내기 전에 부분 발화 처리 및 응답/요약 생성 시작. 체감 레이턴시 대폭 감소.
- https://arxiv.org/abs/2406.15718

### Real-Time Textless Dialogue Generation
- **Yifan He et al., 2025**
- 텍스트 없이 오디오에서 직접 대화하는 모델. 자연스러운 턴테이킹, 백채널, 웃음, 부수 언어 신호 처리.
- **인사이트**: 미래 방향 — ASR→LLM→TTS 캐스케이드를 단일 E2E 모델로 대체. 레이턴시 감소 + 풍부한 회의 역학 캡처.
- https://arxiv.org/abs/2501.04877

---

## 17. TTS & 음성 파이프라인

### SpeakStream — Streaming Text-to-Speech with Interleaved Data
- **Ziqian Ning et al., 2025**
- Decoder-only 스트리밍 TTS. 스트리밍 텍스트 입력에서 증분적 오디오 생성. M4 Pro에서 TTS 30ms + 보코더 15ms = 총 45ms 레이턴시.
- **인사이트**: TODO #11(TTS 기반 음성 안내)에 직접 관련. LLM 스트리밍 출력과 자연스럽게 연결되어 즉각적인 음성 응답.
- https://arxiv.org/abs/2505.19206

### Toward Low-Latency End-to-End Voice Agents for Telecommunications
- **Oleg Balin et al., 2025**
- 스트리밍 ASR(Conformer, RTF<0.2) + 4비트 양자화 LLM + RAG + 실시간 TTS를 모듈형 멀티스레드 파이프라인으로 통합.
- **인사이트**: MeetingMind 풀 파이프라인의 청사진. 4비트 양자화로 품질 유지하면서 연산 대폭 절감. TODO #12(파이프라인 오버랩)와 직접 연관.
- https://arxiv.org/abs/2508.04721

---

## 18. 엣지/온디바이스 & 멀티모달

### Real-Time Smart Meeting Assistant Using Edge AI
- **Senthilselvi et al., 2025**
- ESP32S3 엣지 디바이스 + FastAPI + Tiny LLaMA. WER 7.3%, 액션 아이템 정밀도 85.7%, 화자 분리 89.5%, E2E 레이턴시 3.2초.
- **인사이트**: MeetingMind와 직접 비교 가능한 아키텍처. 레이턴시/정확도 벤치마크 참고. Tiny LLaMA 엣지 배포 사례.
- https://doi.org/10.1109/ICCDS64403.2025.11209202

### TinyLLM — Training and Deploying Language Models at the Edge
- **Akshyat Shah et al., 2024**
- 30-120M 파라미터 소형 모델이 신중한 데이터 큐레이션으로 특정 태스크에서 대형 모델 능가. 로컬 실행으로 네트워크 의존성/프라이버시 해결.
- **인사이트**: 토픽 감지, 액션 아이템 추출 등 특정 태스크에 소형 모델 로컬 실행. 네트워크 왕복 제거로 즉각 결과.
- https://arxiv.org/abs/2412.15304

### Summarization of Multimodal Presentations with Vision-Language Models
- **Xiangyuan Xian et al., 2025**
- 슬라이드, 추출 텍스트, 비디오 프레임, 전사 오디오를 시간 정렬로 결합한 프레젠테이션 요약.
- **인사이트**: 화면 공유/프레젠테이션이 포함된 회의에서 슬라이드 + 음성 전사를 시간 정렬로 융합. 더 풍부한 요약 생성.
- https://arxiv.org/abs/2504.10049

---

## MeetingMind 최적화 방향 요약

위 논문들에서 도출한 실행 가능한 최적화 방향:

### 즉시 적용 가능 (Low-hanging fruit)
| 방향 | 관련 논문 | 예상 효과 |
|------|----------|----------|
| Distil-Whisper로 교체 | Distil-Whisper | 5.8배 빠른 STT, 환각 감소 |
| LLM 기반 ASR 후처리 | ASR Error Correction, Evolutionary Prompt | 도메인 용어 오인식 대폭 감소 (TODO #13) |
| 화자 재할당 후처리 | Once More Diarization, DiarizationLM | 화자 혼동 40-55% 교정 |
| 구두점 복원 추가 | Transformers for DA Recognition | 후속 NLP 태스크 정확도 향상 |

### 중기 개선 (Architecture changes)
| 방향 | 관련 논문 | 예상 효과 |
|------|----------|----------|
| 이중 버퍼 파이프라인 오버랩 | Low-Latency Voice Agent, Duplex Models | 발화 간 레이턴시 대폭 감소 (TODO #12) |
| StreamingLLM 적용 | StreamingLLM (Attention Sinks) | 긴 회의에서 컨텍스트 윈도우 제한 해소 |
| 적응형 요약 정책 | Online Meeting Summarization Policies | 실시간 부분 요약 품질/타이밍 최적화 |
| RAGate 선별적 검색 | RAGate | 불필요한 검색 레이턴시 제거 |
| 쿼리 기반 요약 | QMSum | "예산 결정은?" 같은 타겟 질문 지원 |
| 결정 감지 FSM | Real-time Decision Detection | 이슈→제안→수락 패턴 실시간 감지 |

### 장기 발전 (Next-generation)
| 방향 | 관련 논문 | 예상 효과 |
|------|----------|----------|
| Simul-Whisper 스트리밍 | Simul-Whisper | 체감 STT 레이턴시 ~1초 |
| 비지도 도메인 적응 (STAR) | STAR | 라벨 없이 특정 회의 환경 적응 |
| EEND 겹침 발화 처리 | EEND | 동시 발화 프레임 레벨 처리 |
| Moshi 풀듀플렉스 | Moshi | 200ms 이내 실시간 응답 |
| 멀티모달 융합 | Multimodal Presentation Summary | 슬라이드+음성 통합 분석 |
| SpeakStream TTS | SpeakStream | 45ms TTS 레이턴시 (TODO #11) |
