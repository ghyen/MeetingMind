"""사내 문서를 ChromaDB에 인덱싱하는 스크립트.

사용법:
  python scripts/index_documents.py data/docs/

지원 형식: .txt, .md
각 파일을 하나의 문서로 인덱싱합니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import chromadb

# 프로젝트 루트를 import 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings


def index_directory(doc_dir: str) -> None:
    doc_path = Path(doc_dir)
    if not doc_path.is_dir():
        print(f"디렉토리가 존재하지 않습니다: {doc_dir}")
        sys.exit(1)

    client = chromadb.PersistentClient(path=settings.chromadb_path)
    collection = client.get_or_create_collection("documents")

    files = list(doc_path.glob("**/*.txt")) + list(doc_path.glob("**/*.md"))
    if not files:
        print(f"인덱싱할 문서가 없습니다 ({doc_dir})")
        return

    ids = []
    documents = []
    metadatas = []

    for f in files:
        content = f.read_text(encoding="utf-8").strip()
        if not content:
            continue
        doc_id = str(f.relative_to(doc_path))
        ids.append(doc_id)
        documents.append(content)
        metadatas.append({"title": f.stem, "path": str(f)})

    if not ids:
        print("내용이 있는 문서가 없습니다.")
        return

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"{len(ids)}개 문서 인덱싱 완료 → {settings.chromadb_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/index_documents.py <문서_디렉토리>")
        sys.exit(1)
    index_directory(sys.argv[1])
