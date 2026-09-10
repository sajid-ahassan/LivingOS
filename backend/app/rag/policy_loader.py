from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_policy_text(file_path: Path) -> str:
    if file_path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("Only Markdown and text policies are supported.")

    if not file_path.exists():
        raise FileNotFoundError(f"Policy file not found: {file_path}")

    text = file_path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError("Policy file is empty.")

    return text


def split_policy_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )

    return [
        chunk.strip()
        for chunk in splitter.split_text(text)
        if chunk.strip()
    ]