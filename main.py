from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from wordcloud import WordCloud
import tempfile
import os
import base64
from io import BytesIO

app = FastAPI()

# ✅ CORS設定（フロント側のURLのみ許可）
origins = [
    "http://localhost:3000",                   # 開発用（Next.js Dev Server）
    "https://my-next-app.onrender.com",        # Render上のNext.js（もしRenderにホストしている場合）
    "https://my-patent-app.pages.dev",         # Cloudflare Pages本番
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ルート確認（Renderのヘルスチェック対応）
@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI is running"}

@app.get("/health")
def health():
    return {"ok": True}

# ✅ フォントパス（Render用に相対パス修正）
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-VariableFont_wght.ttf")
if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"フォントファイルが見つかりません: {FONT_PATH}")

@app.post("/generate-wordcloud")
async def generate_wordcloud(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        df = pd.read_csv(tmp_path)
        os.remove(tmp_path)

        column_name = "発明の名称"
        if column_name not in df.columns:
            return JSONResponse(status_code=400, content={"error": f"CSVに '{column_name}' 列がありません"})

        text = " ".join(df[column_name].dropna().astype(str))
        if not text.strip():
            return JSONResponse(status_code=400, content={"error": "有効なテキストデータがありません"})

        wc = WordCloud(
            font_path=FONT_PATH,
            width=800,
            height=600,
            background_color="white",
            max_words=100,
            colormap="viridis"
        ).generate(text)

        img_buffer = BytesIO()
        wc.to_image().save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

        return JSONResponse(content={
            "success": True,
            "image": f"data:image/png;base64,{img_base64}",
            "word_count": len(text.split())
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"処理中にエラーが発生しました: {str(e)}"})
