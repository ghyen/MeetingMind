"""오디오 포맷 통합 변환 — 다양한 음성 파일을 16kHz mono float32 PCM으로 변환.

지원 포맷:
  soundfile 기반: wav, flac, ogg, mp3, aiff, caf, w64, rf64
  ffmpeg 기반 (설치 시): m4a, aac, webm, wma, amr, opus + 위 포맷

출력: numpy float32 배열, 16kHz, mono
"""

from __future__ import annotations

import io
import logging
import subprocess
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

TARGET_SR = 16000

# soundfile이 직접 지원하는 확장자
_SOUNDFILE_EXTS = {
    ".wav", ".flac", ".ogg", ".mp3", ".aiff", ".aif",
    ".caf", ".w64", ".rf64", ".au", ".raw",
}

# ffmpeg가 필요한 확장자
_FFMPEG_EXTS = {
    ".m4a", ".aac", ".webm", ".wma", ".amr", ".opus",
    ".mp4", ".mkv", ".avi", ".mov",
}


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _resample(data: np.ndarray, src_sr: int, target_sr: int) -> np.ndarray:
    """선형 보간 리샘플링."""
    if src_sr == target_sr:
        return data
    target_len = int(len(data) * target_sr / src_sr)
    return np.interp(
        np.linspace(0, len(data) - 1, target_len),
        np.arange(len(data)),
        data,
    ).astype(np.float32)


def _to_mono(data: np.ndarray) -> np.ndarray:
    """스테레오+ → 모노."""
    if data.ndim > 1:
        return data.mean(axis=1).astype(np.float32)
    return data


def convert_file(file_path: str | Path) -> np.ndarray:
    """파일 경로 → 16kHz mono float32 numpy 배열."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일 없음: {path}")

    ext = path.suffix.lower()

    if ext in _SOUNDFILE_EXTS:
        return _convert_soundfile(path)
    elif ext in _FFMPEG_EXTS:
        return _convert_ffmpeg(path)
    else:
        # 확장자 모르면 soundfile 먼저 시도 → 실패 시 ffmpeg
        try:
            return _convert_soundfile(path)
        except Exception:
            return _convert_ffmpeg(path)


def convert_bytes(data: bytes, filename: str = "audio.wav") -> np.ndarray:
    """바이트 데이터 → 16kHz mono float32 numpy 배열."""
    ext = Path(filename).suffix.lower()

    if ext in _SOUNDFILE_EXTS or not ext:
        try:
            return _convert_soundfile_bytes(data)
        except Exception:
            pass

    if ext in _FFMPEG_EXTS or ext not in _SOUNDFILE_EXTS:
        return _convert_ffmpeg_bytes(data, ext)

    raise ValueError(f"지원하지 않는 오디오 포맷: {ext}")


def _convert_soundfile(path: Path) -> np.ndarray:
    import soundfile as sf
    data, sr = sf.read(str(path), dtype="float32")
    data = _to_mono(data)
    return _resample(data, sr, TARGET_SR)


def _convert_soundfile_bytes(raw: bytes) -> np.ndarray:
    import soundfile as sf
    data, sr = sf.read(io.BytesIO(raw), dtype="float32")
    data = _to_mono(data)
    return _resample(data, sr, TARGET_SR)


def _convert_ffmpeg(path: Path) -> np.ndarray:
    if not _has_ffmpeg():
        raise RuntimeError(
            f"'{path.suffix}' 포맷은 ffmpeg가 필요합니다. "
            "brew install ffmpeg 으로 설치하세요."
        )
    result = subprocess.run(
        [
            "ffmpeg", "-i", str(path),
            "-f", "f32le",       # float32 little-endian PCM
            "-acodec", "pcm_f32le",
            "-ar", str(TARGET_SR),
            "-ac", "1",          # mono
            "-v", "error",
            "pipe:1",
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 변환 실패: {result.stderr.decode()[:200]}")
    return np.frombuffer(result.stdout, dtype=np.float32)


def _convert_ffmpeg_bytes(raw: bytes, ext: str) -> np.ndarray:
    """ffmpeg로 바이트 변환. m4a 등 seek 필요한 포맷은 임시 파일 사용."""
    import tempfile
    if not _has_ffmpeg():
        raise RuntimeError(
            f"'{ext}' 포맷은 ffmpeg가 필요합니다. "
            "brew install ffmpeg 으로 설치하세요."
        )
    with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
        tmp.write(raw)
        tmp.flush()
        return _convert_ffmpeg(Path(tmp.name))


def get_supported_extensions() -> list[str]:
    """지원하는 확장자 목록."""
    exts = sorted(_SOUNDFILE_EXTS)
    if _has_ffmpeg():
        exts += sorted(_FFMPEG_EXTS)
    return exts
