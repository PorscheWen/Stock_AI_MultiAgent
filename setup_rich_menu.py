"""
LINE Rich Menu 一鍵部署腳本
執行方式：python setup_rich_menu.py

功能：
1. 用 Pillow 生成 2500x1686 Rich Menu 圖片
2. 透過 LINE API 建立 Rich Menu 設定
3. 上傳圖片
4. 設為全使用者預設選單
"""
import os, sys, io, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from dotenv import load_dotenv
load_dotenv()

from linebot import LineBotApi
from linebot.models import (
    RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, MessageAction
)

ACCESS_TOKEN = os.getenv("CHANNEL_STOCK_ACCESS_TOKEN", "")
if not ACCESS_TOKEN:
    sys.exit("❌ 找不到 CHANNEL_STOCK_ACCESS_TOKEN，請確認 .env 設定")

api = LineBotApi(ACCESS_TOKEN)

# ── 尺寸常數 ──────────────────────────────────────────────────────────────────
W, H   = 2500, 1686
ROWS, COLS = 2, 3
CW, CH = W // COLS, H // ROWS

# ── 選單項目 ─────────────────────────────────────────────────────────────────
# (row, col, 英文主標, 中文副標, 觸發文字, 深色背景, 淺色背景)
ITEMS = [
    (0, 0, "PORTFOLIO",   "查看持股",   "查看持股",   "#0D47A1", "#1E88E5"),
    (0, 1, "AI ANALYSIS", "分析持股",   "分析持股",   "#4A148C", "#8E24AA"),
    (0, 2, "PRICE",       "即時股價",   "股價",       "#004D40", "#00897B"),
    (1, 0, "SCREENSHOT",  "截圖匯入",   "截圖匯入",   "#BF360C", "#F4511E"),
    (1, 1, "ADD STOCK",   "新增持股",   "新增持股",   "#1B5E20", "#43A047"),
    (1, 2, "HELP",        "幫助指令",   "幫助",       "#212121", "#546E7A"),
]

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ── 幾何圖示定義（比例座標，相對於格子） ─────────────────────────────────────
ICONS = {
    "PORTFOLIO":   [("R",.20,.28,.80,.52), ("L",.20,.64,.80,.64), ("L",.20,.74,.60,.74)],
    "AI ANALYSIS": [("C",.50,.35,.15),    ("L",.30,.60,.70,.60), ("L",.38,.72,.62,.72)],
    "PRICE":       [("R",.22,.22,.78,.68),("L",.35,.42,.65,.42), ("L",.35,.54,.65,.54)],
    "SCREENSHOT":  [("R",.18,.26,.82,.72),("C",.50,.49,.13)],
    "ADD STOCK":   [("L",.50,.28,.50,.72),("L",.28,.50,.72,.50)],
    "HELP":        [("C",.50,.33,.13),    ("L",.50,.52,.50,.64), ("C",.50,.74,.05)],
}

def generate_menu_image() -> bytes:
    """生成 Rich Menu PNG（DejaVu Sans Bold，英文+中文副標）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        sys.exit("❌ pip install Pillow")

    img  = Image.new("RGB", (W, H), "#0A0E1A")
    draw = ImageDraw.Draw(img)

    FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    def fnt(size, bold=True):
        try:    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
        except: return ImageFont.load_default()

    def tw(draw, text, font):
        bb = draw.textbbox((0,0), text, font=font)
        return bb[2]-bb[0], bb[3]-bb[1]

    for row, col, en, zh, _, bg_dk, bg_lt in ITEMS:
        x0, y0 = col*CW, row*CH
        x1, y1 = x0+CW-1, y0+CH-1

        # 垂直漸層
        r0,g0,b0 = hex_rgb(bg_lt)
        r1,g1,b1 = hex_rgb(bg_dk)
        for dy in range(CH):
            t = dy/CH
            draw.line([(x0, y0+dy),(x1, y0+dy)],
                      fill=(int(r0+t*(r1-r0)), int(g0+t*(g1-g0)), int(b0+t*(b1-b0))))

        # 細邊框
        draw.rectangle([x0,y0,x1,y1], outline=(255,255,255,60), width=3)

        # 光澤條（頂部亮帶）
        for dy in range(CH//10):
            alpha = 0.35*(1-dy/(CH//10))
            c = tuple(int(min(255, v+80*alpha)) for v in hex_rgb(bg_lt))
            draw.line([(x0, y0+dy),(x1, y0+dy)], fill=c)

        # 幾何圖示
        IW = 12   # line width
        for spec in ICONS.get(en, []):
            t_ = spec[0]
            if t_ == "C":
                cx=x0+spec[1]*CW; cy=y0+spec[2]*CH; r=spec[3]*CW
                draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=(255,255,255,210), width=IW)
            elif t_ == "R":
                draw.rectangle([x0+spec[1]*CW, y0+spec[2]*CH,
                                 x0+spec[3]*CW, y0+spec[4]*CH],
                                outline=(255,255,255,210), width=IW)
            elif t_ == "L":
                draw.line([x0+spec[1]*CW, y0+spec[2]*CH,
                           x0+spec[3]*CW, y0+spec[4]*CH],
                          fill=(255,255,255,210), width=IW)

        # 英文主標
        sz = 108
        f = fnt(sz)
        while tw(draw, en, f)[0] > CW*0.82 and sz > 44:
            sz -= 6; f = fnt(sz)
        w_,_ = tw(draw, en, f)
        mx = x0+(CW-w_)//2;  my = y0+int(CH*0.60)
        draw.text((mx+3,my+3), en, font=f, fill=(0,0,0,120))
        draw.text((mx,my),     en, font=f, fill=(255,255,255))

        # 中文副標（用 DejaVu 只顯示 ASCII 範圍字符——中文顯示為小方格，
        #           但位置和中文字數合理，用來標示功能位置）
        f2 = fnt(60, bold=False)
        w2,_ = tw(draw, zh, f2)
        hx = x0+(CW-w2)//2;  hy = my+int(CH*0.15)
        draw.text((hx,hy), zh, font=f2, fill=(200,220,255))

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def build_rich_menu():
    areas = []
    for row, col, en, zh, action_text, _, __ in ITEMS:
        areas.append(RichMenuArea(
            bounds=RichMenuBounds(x=col*CW, y=row*CH, width=CW, height=CH),
            action=MessageAction(label=zh, text=action_text),
        ))
    return RichMenu(
        size=RichMenuSize(width=W, height=H),
        selected=True,
        name="主選單",
        chat_bar_text="📊 功能選單",
        areas=areas,
    )


def clear_menus():
    try:
        for m in api.get_rich_menu_list():
            api.delete_rich_menu(m.rich_menu_id)
            print(f"  🗑  刪除舊選單: {m.rich_menu_id}")
    except Exception as e:
        print(f"  ⚠️  清除失敗（可忽略）: {e}")


def main():
    print("=" * 52)
    print("   LINE Rich Menu 部署工具")
    print("=" * 52)

    print("\n[1/4] 清除既有 Rich Menu...")
    clear_menus()

    print("\n[2/4] 建立 Rich Menu 設定...")
    rich_menu_id = api.create_rich_menu(build_rich_menu())
    print(f"  ✅ ID: {rich_menu_id}")

    print("\n[3/4] 生成選單圖片並上傳...")
    img_bytes = generate_menu_image()
    print(f"  📐 {len(img_bytes)//1024} KB")
    os.makedirs("static", exist_ok=True)
    with open("static/rich_menu_preview.jpg","wb") as f: f.write(img_bytes)
    print("  💾 預覽: static/rich_menu_preview.jpg")
    api.set_rich_menu_image(rich_menu_id, "image/jpeg", io.BytesIO(img_bytes))
    print("  ✅ 圖片上傳成功")

    print("\n[4/4] 設為全使用者預設選單...")
    api.set_default_rich_menu(rich_menu_id)
    print(f"  ✅ 套用完成！")

    print("\n" + "=" * 52)
    print("  🎉 Rich Menu 已部署！打開 LINE Bot 即可看到")
    print("=" * 52)


if __name__ == "__main__":
    main()
