# Anime Waifu Skill Distiller

将任何角色蒸馏成 Claude Code 的 **Skill.md** 编码伴侣。

粘贴角色的台词、Wiki 描述或性格设定，AI 自动提取角色特征并生成符合 Claude Code 规范的 Skill 文件。生成的 Skill 能让 Claude 在编码辅助时以该角色的语气、口癖和行为风格进行对话。

<img width="1039" height="1585" alt="image" src="https://github.com/user-attachments/assets/fdc73bc7-a97b-4471-a883-b6442e9840e8" />
<img width="1930" height="1372" alt="image" src="https://github.com/user-attachments/assets/bc373eda-3deb-4cfd-bb4a-212db3132659" />


## 效果预览

输入蕾姆的语料 → 生成 `rem-skill.md` → Claude Code 加载后：

> **User**: 帮我修复这段代码的 null pointer 错误  
> **Assistant**: 哼！Master 又粗心了～ 不过既然是你开口，人家就帮忙看一下… 问题出在这里没有做 null check 呢。在第三行加一个 guard clause 就好了。…真是的，下次注意点啦～

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
uvicorn main:app --reload

# 3. 打开浏览器
# http://localhost:8000
```

在页面右上角 ⚙ 设置中配置 API：

| 提供商 | 需要的信息 |
|--------|-----------|
| Anthropic (Claude) | API Key |
| OpenAI (GPT-4o) | API Key |
| DeepSeek | API Key |
| 自定义 (OpenAI 兼容) | API Key + Base URL + Model |

也可以不填 API Key，直接设置环境变量：`ANTHROPIC_API_KEY`、`OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`。

## 支持模型

- **Anthropic**: Claude Sonnet 4.6, Claude Opus 4.7 等
- **OpenAI**: GPT-4o, GPT-4.1 等
- **DeepSeek**: deepseek-chat, deepseek-reasoner 等
- **自定义**: 任何 OpenAI 兼容 API（Groq、Together、vLLM、Ollama 等）

## 项目结构

```
anime-waifu-skill-distiller/
├── main.py                  # FastAPI 入口
├── services/
│   └── llm.py               # LLM 蒸馏链（特征提取 → Skill生成 → 预览）
├── prompts/
│   ├── extract_traits.txt   # 角色特征提取 prompt
│   └── generate_skill.txt   # Skill.md 生成 prompt
├── templates/
│   └── index.html           # 前端页面（纯静态，深色主题）
├── requirements.txt
└── .env.example
```

## 工作原理

1. **特征提取** — 将原始语料发给 LLM，提取结构化角色特征卡（JSON）
2. **Skill 生成** — 基于特征卡，生成符合 Claude Code 规范的 Skill.md
3. **对话预览** — 生成一段示例对话，展示角色如何回应编码请求

## License

MIT
