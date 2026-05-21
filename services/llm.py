import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from pydantic import BaseModel

load_dotenv()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_CORPUS_LENGTH = int(os.getenv("MAX_CORPUS_LENGTH", "5000"))

# Provider registry: id -> { sdk, default_model, default_base_url }
# sdk="anthropic" uses Anthropic native; sdk="openai" uses OpenAI SDK (works for any compatible API)
PROVIDERS = {
    "anthropic": {
        "sdk": "anthropic",
        "default_model": "claude-sonnet-4-6",
        "default_base_url": "",
    },
    "openai": {
        "sdk": "openai",
        "default_model": "gpt-4o",
        "default_base_url": "https://api.openai.com/v1",
    },
    "deepseek": {
        "sdk": "openai",
        "default_model": "deepseek-chat",
        "default_base_url": "https://api.deepseek.com/v1",
    },
    "custom": {
        "sdk": "openai",
        "default_model": "",
        "default_base_url": "",
    },
}


class CharacterTrait(BaseModel):
    name: str
    core_personality: str
    speech_style: str
    catchphrases: list[str]
    emotional_patterns: str
    coding_attitude: str
    visual_brief: str


def _load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def _call_llm(
    *,
    system_prompt: str,
    user_message: str,
    provider: str,
    api_key: str,
    model: str,
    base_url: str = "",
    max_tokens: int = 1024,
) -> str:
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise ValueError(f"Unknown provider: {provider}")

    if cfg["sdk"] == "anthropic":
        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return msg.content[0].text

    else:  # openai-compatible
        url = base_url or cfg["default_base_url"]
        client = OpenAI(api_key=api_key, base_url=url)
        msg = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return msg.choices[0].message.content


def _resolve_model(provider: str, model: str) -> str:
    """Resolve model: use provided, or fall back to provider default."""
    return model or PROVIDERS.get(provider, {}).get("default_model", "")


def extract_traits(
    corpus: str,
    provider: str = "anthropic",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> CharacterTrait:
    model = _resolve_model(provider, model)
    system_prompt = _load_prompt("extract_traits.txt")

    raw = _call_llm(
        system_prompt=system_prompt,
        user_message=corpus,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        max_tokens=1024,
    )

    raw = _strip_fences(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raw = _call_llm(
            system_prompt=system_prompt + "\n\nCRITICAL: Return ONLY valid JSON. No markdown fences, no extra text.",
            user_message=corpus,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            max_tokens=1024,
        )
        raw = _strip_fences(raw)
        data = json.loads(raw)

    return CharacterTrait(**data)


def generate_skill(
    traits: CharacterTrait,
    intensity: str = "full",
    provider: str = "anthropic",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> str:
    model = _resolve_model(provider, model)
    system_prompt = (
        _load_prompt("generate_skill.txt")
        .replace("{traits_json}", traits.model_dump_json(indent=2))
        .replace("{name}", traits.name)
        .replace("{core_personality}", traits.core_personality)
        .replace("{intensity}", intensity)
    )

    raw = _call_llm(
        system_prompt=system_prompt,
        user_message="请生成完整的Skill.md内容。",
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        max_tokens=2048,
    )

    return _strip_fences(raw)


def generate_preview(
    traits: CharacterTrait,
    intensity: str = "full",
    provider: str = "anthropic",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> str:
    model = _resolve_model(provider, model)

    system_prompt = "你是一个创意写作助手。根据角色特征生成一段符合角色风格的简短对话。"
    user_message = f"""根据以下角色特征，生成一段简短的示例对话。用户说"帮我修复这段代码的null pointer错误"，角色用其独特的语气和风格回复。

角色特征：
- 名字：{traits.name}
- 性格：{traits.core_personality}
- 说话风格：{traits.speech_style}
- 口癖：{', '.join(traits.catchphrases)}
- 情绪模式：{traits.emotional_patterns}

强度：{'完全沉浸式角色扮演' if intensity == 'full' else '轻度角色风格'}

写一个User消息和一个Assistant回复。回复要展示角色的个性，但给出的技术建议必须正确（检查null、添加guard clause等）。回复50-150字。"""

    return _call_llm(
        system_prompt=system_prompt,
        user_message=user_message,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        max_tokens=512,
    ).strip()


def chat(
    skill_md: str,
    message: str,
    provider: str = "anthropic",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> str:
    """Chat with the generated waifu persona. Uses skill_md as the system prompt."""
    model = _resolve_model(provider, model)
    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")

    system_prompt = f"{skill_md}\n\n现在，请严格按照以上角色设定与用户对话。用角色的语气、口癖和风格回复。技术内容必须准确。"

    return _call_llm(
        system_prompt=system_prompt,
        user_message=message,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        max_tokens=1024,
    ).strip()


def distill(
    corpus: str,
    intensity: str = "full",
    provider: str = "anthropic",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> dict:
    if len(corpus) > MAX_CORPUS_LENGTH:
        raise ValueError(f"Corpus too long. Max {MAX_CORPUS_LENGTH} characters, got {len(corpus)}.")

    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}. Supported: {', '.join(PROVIDERS.keys())}")

    if not api_key:
        env_map = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}
        env_var = env_map.get(provider, "API_KEY")
        api_key = os.getenv(env_var, "")
        if not api_key:
            raise RuntimeError(f"No API key provided. Set it in the page settings or the {env_var} env var.")

    traits = extract_traits(corpus, provider, api_key, model, base_url)
    skill_md = generate_skill(traits, intensity, provider, api_key, model, base_url)
    preview = generate_preview(traits, intensity, provider, api_key, model, base_url)

    return {
        "skill_md": skill_md,
        "trait": traits.model_dump(),
        "preview": preview,
    }
