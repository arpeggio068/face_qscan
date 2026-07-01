# print_service.py

from datetime import datetime

import win32print
import win32ui
from PIL import Image, ImageDraw, ImageFont, ImageWin

from config import (
    PRINTER_NAME,
    PRINT_ENABLED,
    TICKET_TITLE,
    TICKET_WIDTH,
)


def thai_date_text(dt=None):
    if dt is None:
        dt = datetime.now()

    thai_days = [
        "จันทร์", "อังคาร", "พุธ", "พฤหัสบดี",
        "ศุกร์", "เสาร์", "อาทิตย์"
    ]

    day_name = thai_days[dt.weekday()]
    buddhist_year = dt.year + 543

    return f"{day_name} {dt.strftime('%d/%m/')}{buddhist_year} {dt.strftime('%H:%M')}"


def short_token(token: str) -> str:
    if not token:
        return ""
    return token[:13]


def load_font(size=32, bold=False):
    font_paths = [
        r"C:\Windows\Fonts\LeelUIsl.ttf",
        r"C:\Windows\Fonts\LeelawUI.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]

    if bold:
        font_paths = [
            r"C:\Windows\Fonts\LeelawUIb.ttf",
            r"C:\Windows\Fonts\tahomabd.ttf",
            r"C:\Windows\Fonts\LeelawUI.ttf",
        ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def draw_center(draw, text, y, font, width=TICKET_WIDTH):
    text = str(text)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (width - text_w) // 2
    draw.text((x, y), text, font=font, fill=0)


def draw_line(draw, y, width=TICKET_WIDTH):
    draw.line((40, y, width - 40, y), fill=0, width=2)


def create_ticket_image(queue_no: str, token: str):
    ref = short_token(token)
    date_text = thai_date_text()

    width = TICKET_WIDTH
    height = 600

    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)

    font_title = load_font(38, bold=True)
    font_date = load_font(24)
    font_label = load_font(30, bold=True)
    font_queue = load_font(110, bold=True)
    font_ref = load_font(22)

    y = 18

    draw_center(draw, TICKET_TITLE, y, font_title)
    y += 58

    draw_center(draw, date_text, y, font_date)
    y += 48

    draw_line(draw, y)
    y += 24

    draw_center(draw, "หมายเลขคิว", y, font_label)
    y += 38

    draw_center(draw, queue_no, y, font_queue)
    y += 138

    draw_line(draw, y)
    y += 28

    draw_center(draw, f"Ref: {ref}", y, font_ref)
    y += 42

    draw_line(draw, y)

    # ตัดความสูงให้พอดีกับเนื้อหา ไม่ให้เปลืองกระดาษ
    padding_bottom = 30
    final_height = y + padding_bottom

    img = img.crop((0, 0, width, final_height))

    return img


def print_image_to_printer(img: Image.Image, printer_name: str):
    dc = win32ui.CreateDC()
    dc.CreatePrinterDC(printer_name)

    printable_area = dc.GetDeviceCaps(8), dc.GetDeviceCaps(10)
    printer_width = printable_area[0]

    img_w, img_h = img.size

    # scale ให้เต็มหน้ากระดาษตาม printer driver
    scale = printer_width / img_w
    print_w = int(img_w * scale)
    print_h = int(img_h * scale)

    x = 0
    y = 0

    dc.StartDoc("Queue Ticket")
    dc.StartPage()

    dib = ImageWin.Dib(img.convert("RGB"))
    dib.draw(dc.GetHandleOutput(), (x, y, x + print_w, y + print_h))

    dc.EndPage()
    dc.EndDoc()
    dc.DeleteDC()


def print_queue_ticket(queue_no: str, token: str):
    if not PRINT_ENABLED:
        print("[PRINT] disabled")
        return False

    printer_name = PRINTER_NAME or win32print.GetDefaultPrinter()
    ref = short_token(token)

    try:
        img = create_ticket_image(queue_no, token)
        print_image_to_printer(img, printer_name)

        print(f"[PRINT] queue={queue_no}, ref={ref}, printer={printer_name}")
        return True

    except Exception as e:
        print("[PRINT ERROR]", e)
        return False


if __name__ == "__main__":
    print_queue_ticket(
        queue_no="001",
        token="6dd51165-6b8c-49e0-b731-5c1ec4e55048"
    )