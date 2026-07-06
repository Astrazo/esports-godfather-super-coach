# Build with: pyinstaller lazy_esports_godfather.spec

from PyInstaller.utils.hooks import collect_all

langchain_data, langchain_binaries, langchain_hidden = collect_all("langchain")
ollama_data, ollama_binaries, ollama_hidden = collect_all("langchain_ollama")
openai_data, openai_binaries, openai_hidden = collect_all("langchain_openai")
anthropic_data, anthropic_binaries, anthropic_hidden = collect_all("langchain_anthropic")
google_data, google_binaries, google_hidden = collect_all("langchain_google_genai")

datas = [
    ("data", "data"),
    ("web/static", "web/static"),
    ("system_prompt.md", "."),
    ("draft_system_prompt.md", "."),
] + langchain_data + ollama_data + openai_data + anthropic_data + google_data

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=(
        langchain_binaries
        + ollama_binaries
        + openai_binaries
        + anthropic_binaries
        + google_binaries
    ),
    datas=datas,
    hiddenimports=(
        langchain_hidden
        + ollama_hidden
        + openai_hidden
        + anthropic_hidden
        + google_hidden
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["streamlit", "plotly"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lazy Esports Godfather",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="Lazy Esports Godfather",
)
