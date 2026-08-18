"""Build a Markdown knowledge base for RAG from app/kb/school_data.json.

Generated documents live in app/kb/docs/ and are the retrieval source for the
RAG engine. Run:

    python scripts/build_kb.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "app" / "kb" / "school_data.json"
OUT = ROOT / "app" / "kb" / "docs"


def _counts(data: dict) -> tuple[int, int]:
    n_colleges = len(data["colleges"])
    n_depts = sum(len(c["depts"]) for c in data["colleges"])
    return n_colleges, n_depts


def render_overview(data: dict) -> str:
    o = data["overview"]
    n_colleges, n_depts = _counts(data)
    college_list = "\n".join(f"- {c['name']}" for c in data["colleges"])
    return f"""# 中国农业大学概况

中国农业大学（英文名 {o['name_en']}，缩写 {o['short']}），创建于{o['founded']}，
是国家{o['type']}。校训为：{o['motto']}。

## 学校简介
{o['intro']}

## 校园与规模
- 办学地点：{o['location']}
- 占地面积：{o['size']}
- 在校学生：{o['students']}
- 师资队伍：{o['faculty']}

## 院系构成
学校现设有{n_colleges}个学院，全院共下设{n_depts}个系（教研机构）：
{college_list}

## 重点学科与代表性成果
{o['achievments_summary']}

## 学科布局
学校形成了以农学、生命科学、农业工程、农业经济管理为核心，农、工、理、经、管、法、文多学科协调发展的学科体系，
其中作物学、园艺学、植物保护、生物学、动物科学（畜牧学）、草学、兽医学、食品科学与工程、农业工程、
农林经济管理、农业水土工程、植物营养学、土壤学等均为国家重点学科或国家'双一流'建设学科。
"""


def render_college(college: dict) -> str:
    header = (
        f"# {college['name']}\n\n"
        f"{college['intro']}\n\n"
        f"## 下设系（{len(college['depts'])}个）\n" + "\n".join(f"- {d}" for d in college["depts"]) + "\n"
    )
    major_blocks = []
    for m in college["majors"]:
        major_blocks.append(
            f"""## 专业：{m['name']}
- 专业方向：{'；'.join(m['directions'])}
- 重点学科：{m['key_discipline']}
- 主要课程：{'、'.join(m['courses'])}
"""
        )
    return header + "\n".join(major_blocks)


def render_professor(p: dict) -> str:
    tag = "（说明：本条目为演示示例数据）" if p.get("demo") else ""
    return f"""# 导师介绍：{p['name']}{tag}

- 职称：{p['title']}
- 所在学院：{p['college']}
- 主要研究方向：{p['research']}

## 重点科研成就
{p['achievements']}
"""


def render_achievement(a: dict) -> str:
    return f"""# 重点科研成果：{a['title']}

{a['desc']}
"""


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    n_colleges, n_depts = _counts(data)
    assert n_colleges == len(data["colleges"])
    assert n_depts == sum(len(c["depts"]) for c in data["colleges"])
    print(f"knowledge base counts -> colleges={n_colleges}, depts={n_depts}")

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.md"):
        old.unlink()

    (OUT / "01_overview.md").write_text(render_overview(data), encoding="utf-8")
    for i, c in enumerate(data["colleges"], start=10):
        (OUT / f"{i:02d}_college_{c['id']}.md").write_text(render_college(c), encoding="utf-8")
    for i, p in enumerate(data["professors"], start=40):
        (OUT / f"{i:02d}_professor_{p['id']}.md").write_text(render_professor(p), encoding="utf-8")
    for i, a in enumerate(data["achievements"], start=60):
        (OUT / f"{i:02d}_achievement_{a['id']}.md").write_text(render_achievement(a), encoding="utf-8")

    print(f"generated {len(list(OUT.glob('*.md')))} documents under {OUT}")


if __name__ == "__main__":
    main()