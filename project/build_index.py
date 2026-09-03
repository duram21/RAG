import numpy as np
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path

MODEL_NAME = "intfloat/multilingual-e5-small"


path = Path("project/data/items.json")
data = json.loads(path.read_text(encoding="utf-8"))

model = SentenceTransformer(MODEL_NAME)


def build_text(item: dict) -> str:
    return (
        f"{item['name']} ({item['gold_total']}골드)\n"
        f"{item['description_text']}"
    )

def main() -> None:
    items = data["items"]
    print(f"아이템 {len(items)}개 읽음")

    records = []
    for item in items:
        if not item["description_text"]:
            continue

        records.append({
            "item_id": item["item_id"],
            "name": item["name"],
            "gold_total": item["gold_total"],
            "text": build_text(item)
        })

    # print(records)

    # embedding
    vectors = model.encode(
        ["passage: " + r["text"] for r in records],
        normalize_embeddings=True,
    )


    # --- 저장 ---
    INDEX_DIR = Path("project/data")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # 벡터: 이진 형식으로
    np.save(INDEX_DIR / "index.npy", vectors)

    # 나머지: JSON 으로
    meta = {
        "model": MODEL_NAME,          # 어떤 모델로 만들었는지 (로드할 때 검증용)
        "dim": int(vectors.shape[1]),
        "count": len(records),
        "records": records,
    }
    (INDEX_DIR / "index.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"저장 완료: {vectors.shape} 벡터 + records {len(records)}개")




if __name__ == "__main__":
    main()