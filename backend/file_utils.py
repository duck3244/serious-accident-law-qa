"""업로드 파일에서 평문 텍스트 추출 (txt / docx / pdf)"""
import io

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = ("txt", "docx", "pdf")


def extract_text(filename: str, data: bytes) -> str:
    """업로드된 파일 바이트에서 평문 텍스트를 추출한다.

    Args:
        filename: 원본 파일명 (확장자 판별용)
        data: 파일 바이트

    Returns:
        추출된 텍스트

    Raises:
        ValueError: 지원하지 않는 확장자인 경우
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "txt":
        return data.decode("utf-8", errors="replace")

    if ext == "docx":
        doc = Document(io.BytesIO(data))
        return "\n".join(para.text for para in doc.paragraphs)

    if ext == "pdf":
        reader = PdfReader(io.BytesIO(data))
        # 이미지 전용 페이지 등은 None을 반환할 수 있어 빈 문자열로 보정
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    raise ValueError(
        f"지원하지 않는 파일 형식입니다: '.{ext}' "
        f"(지원 형식: {', '.join(SUPPORTED_EXTENSIONS)})"
    )
