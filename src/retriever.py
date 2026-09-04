"""RAG 파이프라인 (Day2 패턴).

1일차 5번: `data/guides/`의 체크리스트 문서 2개를 인덱싱하고 검색하는 `retriever`를
만든다. `security_agent`(등)에 검색 도구로 연결하는 건 1일차 4번(Agent 생성)이 실제로
동작하는 것을 확인한 뒤 이어간다.
"""

import os
from pathlib import Path

from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

_GUIDES_DIR = Path(__file__).resolve().parent.parent / "data" / "guides"


def default_embeddings() -> BedrockEmbeddings:
    """환경변수 `EMBED_MODEL_ID`로 지정된 Bedrock 임베딩 모델을 생성해 반환한다.

    `_default_llm()`(채팅 모델)과 마찬가지로, 임베딩 모델도 이 함수 한 곳에서만 만든다 —
    모델을 바꾸려면 `.env`의 `EMBED_MODEL_ID`만 바꾸면 된다(모델 독립성, 조건 9).
    공개 함수(밑줄 없음)인 이유는 3일차 3번(ragas 지표 산출)의 `context_precision` 등도
    같은 임베딩 생성점을 재사용해야 하기 때문이다(모듈 밖에서 호출).
    """
    model_id = os.environ["EMBED_MODEL_ID"]
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    return BedrockEmbeddings(model_id=model_id, region_name=region)


def _load_guide_documents(guides_dir: Path | None = None) -> list[Document]:
    """`data/guides/`의 마크다운 체크리스트 문서를 읽어 청크로 나눈다(Day2 패턴).

    먼저 `##` 제목 단위로 나누고(체크리스트 항목 하나가 검색 단위가 되게), 항목이 너무
    길면 다시 글자 수 기준으로 잘게 쪼갠다.
    """
    guides_dir = guides_dir or _GUIDES_DIR
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("##", "section")])
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    documents: list[Document] = []
    for path in sorted(guides_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        for header_chunk in header_splitter.split_text(content):
            for piece in text_splitter.split_text(header_chunk.page_content):
                documents.append(
                    Document(page_content=piece, metadata={"doc_id": path.stem, **header_chunk.metadata})
                )
    return documents


class Retriever:
    """RAG 검색기 — `data/guides/`의 체크리스트 문서에서 근거를 검색한다.

    벡터 인덱스는 첫 검색 시점에 한 번만 만들어 인스턴스에 캐싱한다(어댑터의 스캔 결과
    캐싱과 같은 패턴).
    """

    def __init__(self, guides_dir: Path | None = None) -> None:
        self.guides_dir = guides_dir or _GUIDES_DIR
        self._vectorstore: Chroma | None = None

    def _ensure_index(self) -> Chroma:
        if self._vectorstore is None:
            documents = _load_guide_documents(self.guides_dir)
            self._vectorstore = Chroma.from_documents(documents, embedding=default_embeddings())
        return self._vectorstore

    def search(self, query: str, k: int = 3) -> list[dict[str, str]]:
        """질의와 관련된 문서 조각을 검색해 `{doc_id, text}` 리스트로 반환한다(API 스펙과 동일 모양)."""
        vectorstore = self._ensure_index()
        results = vectorstore.similarity_search(query, k=k)
        return [{"doc_id": doc.metadata.get("doc_id", "unknown"), "text": doc.page_content} for doc in results]


retriever = Retriever()
