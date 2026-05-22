from services.llm import _strip_fences, _resolve_model


class TestStripFences:
    def test_fenced_code_block(self):
        assert _strip_fences("```\nhello\n```") == "hello"

    def test_fenced_with_language_tag(self):
        assert _strip_fences("```json\n{\"a\": 1}\n```") == '{"a": 1}'

    def test_no_fence_passthrough(self):
        assert _strip_fences("plain text") == "plain text"

    def test_empty_string(self):
        assert _strip_fences("") == ""

    def test_inline_code_not_stripped(self):
        assert _strip_fences("`single backtick`") == "`single backtick`"

    def test_multiline_content(self):
        assert _strip_fences("```\nline1\nline2\n```") == "line1\nline2"

    def test_whitespace_around_fences(self):
        assert _strip_fences("  \n```\nhello\n```\n  ") == "hello"

    def test_only_opening_fence_no_closing(self):
        assert _strip_fences("```\njust text\nno closing") == "just text\nno closing"

    def test_trailing_newline_in_fenced(self):
        assert _strip_fences("```\nhello\n\n```") == "hello\n"


class TestResolveModel:
    def test_explicit_model_wins(self):
        assert _resolve_model("anthropic", "custom-model") == "custom-model"

    def test_fallback_anthropic_default(self):
        assert _resolve_model("anthropic", "") == "claude-sonnet-4-6"

    def test_fallback_deepseek_default(self):
        assert _resolve_model("deepseek", "") == "deepseek-chat"

    def test_fallback_openai_default(self):
        assert _resolve_model("openai", "") == "gpt-4o"

    def test_unknown_provider_no_model(self):
        assert _resolve_model("nonexistent", "") == ""

    def test_unknown_provider_explicit_model(self):
        assert _resolve_model("nonexistent", "my-model") == "my-model"
