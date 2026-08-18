# 中国农业大学数字人模拟平台

一个面向中国农业大学的 **数字人 + RAG + LLM** 问答模拟平台：

- 数字人「农小田」在网页上以拟人姿态呈现（眨眼、点头、微笑、挥手、思考等），回答时口型随
  语音实时联动，并通过 **语音播报**（TTS）朗读回答。
- 回答基于 **学校知识库 RAG 检索**（学校概况 / 学院与院系构成 / 专业·方向·重点学科·主要课程 /
  导师介绍 / 重点科研成就），再交给 **DeepSeek LLM** 组织自然语言回答。
- 后端为 **RESTful API**（FastAPI），前端为纯静态页面；支持中文语音输入（Web Speech API）。

```
浏览器 ──HTTP──▶ FastAPI RESTful API
                    │
                    ├─ /api/v1/chat     内容生成
                    │      ├─ RAG 检索（jieba + BM25 知识库索引）
                    │      └─ DeepSeek LLM（OpenAI 兼容，离线自动降级为演示模式）
                    ├─ /api/v1/avatar/speak  语音合成（Edge TTS，离线降级为无声 wav）
                    └─ /api/v1/kb/*     结构化知识库查询
```

## 功能清单

| 编号 | 功能 | 说明 |
| --- | --- | --- |
| 1 | 回答用户提问 | `/api/v1/chat`，支持多轮对话历史 |
| 2 | 学校概况 + 学院/系构成 | 21 个学院全量数据，院系数量由数据自动统计，内置各学院简介 |
| 3 | 专业介绍 | 每个专业的方向、重点学科、主要课程 |
| 4 | 导师介绍与科研成就 | 含院士等主要导师的研究方向与重点成果，另有重点科研成果专题 |
| 5 | RAG 知识库 | 知识文档自动由结构化数据生成，jieba 分词 + BM25 检索 |
| 6 | 网页访问 + RESTful API | FastAPI 提供服务，前端静态页面直连 |
| 7 | DeepSeek LLM | OpenAI 兼容接口接入深求索；未配置 Key 时自动进入离线演示模式 |
| 8 | 拟人数字人 + 语音播报 | Canvas 数字人动画（口型随音频联动）+ Edge TTS 语音 |
| 9 | Python 实现并通过测试 | `pytest` 全部用例通过 |

## 目录结构

```
cau-dhuman/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置（支持 .env）
│   ├── schemas.py         # API 数据模型
│   ├── kb/school_data.json   # 学校知识库结构化数据（数据源）
│   ├── kb/docs/*.md       # 由数据自动生成的检索文档
│   ├── rag/               # 分词 / BM25 / 索引 / 检索
│   ├── llm/deepseek.py    # DeepSeek 客户端（含离线演示降级）
│   ├── dh/tts.py          # Edge TTS 语音合成（含离线降级）
│   └── api/               # chat / knowledge / avatar 路由
├── scripts/build_kb.py    # 由 school_data.json 生成 RAG 文档
├── static/                # 前端（数字人动画、对话界面）
├── audio/                 # TTS 音频缓存
└── tests/                 # pytest 测试
```

## 快速开始

```bash
cd cau-dhuman
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 可选：填写 DeepSeek API Key（填入 .env，不填则以离线演示模式运行，功能可全流程体验）
cp .env.example .env   # 编辑 .env 填入 DEEPSEEK_API_KEY

# 生成知识库检索文档并启动服务
.venv/bin/python scripts/build_kb.py
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

浏览器打开 <http://localhost:8000> 即可与数字人「农小田」对话。

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/chat` | 提问（RAG+LLM，可选语音播报），返回 `answer/audio_url/sources` |
| GET | `/api/v1/kb/overview` | 学校概况（含自动统计的学院数/系总数） |
| GET | `/api/v1/kb/colleges` | 学院列表 |
| GET | `/api/v1/kb/colleges/{id}` | 学院详情（系构成 + 专业方向/重点学科/课程） |
| GET | `/api/v1/kb/majors` | 全部专业 |
| GET | `/api/v1/kb/professors` | 导师列表 |
| GET | `/api/v1/kb/professors/{id}` | 导师详情（研究方向 + 科研成就） |
| GET | `/api/v1/kb/achievements` | 重点科研成就 |
| POST | `/api/v1/avatar/speak` | 文本转语音 |
| GET | `/api/v1/avatar/voices` | 可用音色（女声晓晓 / 男声云扬） |
| GET | `/healthz` | 健康检查（LLM 连接状态 + 知识库规模） |

`POST /api/v1/chat` 请求示例：

```json
{
  "message": "动物科技学院有哪些专业和主要课程？",
  "history": [],
  "voice": "female",
  "use_tts": true
}
```

## 测试

```bash
.venv/bin/python -m pytest tests/ -v
```

测试覆盖：分词与 BM25 排序、RAG 检索相关性、知识库各端点的数据一致性、
聊天端点的 RAG 接地回答与 TTS 降级、离线语音合成回退等。

## 说明

- 知识库为教学演示用途，数据根据公开资料整编；个别导师条目标有「示例」字样，仅作展示。
- DeepSeek 为 OpenAI 兼容接口，需在 `.env` 配置 `DEEPSEEK_API_KEY`；未配置时自动降级为
  离线演示模式（同样走 RAG 检索，便于全流程演示与测试）。
- 语音合成依赖 Edge TTS 在线服务；离线时会自动降级为无声音频，数字人口型仍会随“说话”联动。