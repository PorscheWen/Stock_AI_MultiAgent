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
    RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds,
    MessageAction, URIAction
)

ACCESS_TOKEN = os.getenv("CHANNEL_STOCK_ACCESS_TOKEN", "")
if not ACCESS_TOKEN:
    sys.exit("❌ 找不到 CHANNEL_STOCK_ACCESS_TOKEN，請確認 .env 設定")

# PWA 網址（部署後填入，例：https://your-app.onrender.com/app）
APP_URL = os.getenv("APP_URL", "https://your-app.onrender.com/app")

api = LineBotApi(ACCESS_TOKEN)

# ── 尺寸常數 ──────────────────────────────────────────────────────────────────
W, H   = 2500, 1686
ROWS, COLS = 2, 3
CW, CH = W // COLS, H // ROWS

# ── 選單項目 ─────────────────────────────────────────────────────────────────
# (row, col, 英文標籤, action_type, action_value, 深色背景, 淺色背景, 圖示key)
ITEMS = [
    (0, 0, "PORTFOLIO",  "msg", "查看持股", "#0D47A1", "#1E88E5", "PORTFOLIO"),
    (0, 1, "AI ANALYSIS","msg", "分析持股", "#4A148C", "#8E24AA", "AI"),
    (0, 2, "PRICE",      "msg", "股價",     "#004D40", "#00897B", "PRICE"),
    (1, 0, "SCREENSHOT", "msg", "截圖匯入", "#BF360C", "#F4511E", "SCREENSHOT"),
    (1, 1, "PWA APP",    "uri", APP_URL,    "#1A237E", "#3949AB", "WEBAPP"),
    (1, 2, "HELP",       "msg", "幫助",     "#212121", "#546E7A", "HELP"),
]

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ── 圖示定義：所有 y 座標限制在 0.50 以內，避免遮住底部文字標籤 ─────────
# 格式：("R",x1,y1,x2,y2) | ("C",cx,cy,r) | ("L",x1,y1,x2,y2)
ICONS = {
    # 持股：長條圖（bar chart）
    "PORTFOLIO": [
        ("R", .18,.36,.34,.50),   # 短柱
        ("R", .41,.24,.57,.50),   # 中柱
        ("R", .64,.10,.80,.50),   # 高柱
        ("L", .14,.50,.84,.50),   # X 軸
    ],
    # AI 分析：神經網絡節點
    "AI": [
        ("C", .50,.18,.10),        # 頂部節點
        ("C", .26,.38,.08),        # 左節點
        ("C", .74,.38,.08),        # 右節點
        ("L", .50,.28,.26,.30),   # 連線左
        ("L", .50,.28,.74,.30),   # 連線右
        ("C", .50,.48,.08),        # 底部節點
    ],
    # 股價：折線圖
    "PRICE": [
        ("L", .13,.45,.30,.28),
        ("L", .30,.28,.48,.38),
        ("L", .48,.38,.66,.14),
        ("L", .66,.14,.84,.25),
        ("L", .10,.50,.88,.50),   # X 軸
    ],
    # 截圖：手機框
    "SCREENSHOT": [
        ("R", .30,.06,.70,.50),   # 手機外框
        ("C", .50,.26,.10),        # 鏡頭
        ("L", .42,.46,.58,.46),   # 主頁鍵
    ],
    # PWA：瀏覽器視窗
    "WEBAPP": [
        ("R", .12,.06,.88,.50),   # 外框
        ("L", .12,.20,.88,.20),   # 標題欄分隔線
        ("C", .24,.13,.05),        # 視窗按鈕1
        ("C", .36,.13,.05),        # 視窗按鈕2
        ("L", .46,.08,.82,.08),   # 地址列（上）
        ("L", .46,.18,.82,.18),   # 地址列（下）
        ("L", .20,.30,.80,.30),   # 內容線1
        ("L", .20,.39,.80,.39),   # 內容線2
        ("L", .20,.48,.68,.48),   # 內容線3
    ],
    # 幫助：問號
    "HELP": [
        ("C", .50,.16,.11),        # ? 頂部圓弧
        ("L", .50,.27,.50,.41),   # ? 竪
        ("C", .50,.48,.04),        # ? 點
    ],
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

    for row, col, en, atype, aval, bg_dk, bg_lt, icon_key in ITEMS:
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

        # 幾何圖示（全部限制在格子上半部 y ≤ 0.52）
        IW = 12   # line width
        ICON_SCALE = 0.82  # 圖示佔格子高度的比例（縮放至前 55% 空間）
        for spec in ICONS.get(icon_key, []):
            t_ = spec[0]
            if t_ == "C":
                cx=x0+spec[1]*CW; cy=y0+spec[2]*CH*ICON_SCALE; r=spec[3]*CW
                draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline=(255,255,255,210), width=IW)
            elif t_ == "R":
                draw.rectangle([x0+spec[1]*CW, y0+spec[2]*CH*ICON_SCALE,
                                 x0+spec[3]*CW, y0+spec[4]*CH*ICON_SCALE],
                                outline=(255,255,255,210), width=IW)
            elif t_ == "L":
                draw.line([x0+spec[1]*CW, y0+spec[2]*CH*ICON_SCALE,
                           x0+spec[3]*CW, y0+spec[4]*CH*ICON_SCALE],
                          fill=(255,255,255,210), width=IW)

        # 英文標籤（位於格子下方 65% 處）
        sz = 108
        f = fnt(sz)
        while tw(draw, en, f)[0] > CW*0.82 and sz > 44:
            sz -= 6; f = fnt(sz)
        w_,_ = tw(draw, en, f)
        mx = x0+(CW-w_)//2;  my = y0+int(CH*0.65)
        draw.text((mx+3,my+3), en, font=f, fill=(0,0,0,120))
        draw.text((mx,my),     en, font=f, fill=(255,255,255))

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def build_rich_menu():
    areas = []
    for row, col, en, atype, aval, bg_dk, bg_lt, icon_key in ITEMS:
        if atype == "uri":
            action = URIAction(label=en[:20], uri=aval)
        else:
            action = MessageAction(label=en[:20], text=aval)
        areas.append(RichMenuArea(
            bounds=RichMenuBounds(x=col*CW, y=row*CH, width=CW, height=CH),
            action=action,
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
