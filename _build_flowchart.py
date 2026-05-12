"""
Генерирует блок-схему алгоритма работы средства проверки (ГОСТ 19.701-90).
Запуск:  python _build_flowchart.py   ->   flowchart.png
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle, FancyBboxPatch


FONT = {"family": "DejaVu Sans", "size": 10}
W, H = 5.0, 1.0


def _text(ax, x, y, s, **kw):
    ax.text(x, y, s, ha="center", va="center", fontdict=FONT, **kw)


def terminator(ax, x, y, text):
    box = FancyBboxPatch(
        (x - W / 2, y - H / 2), W, H,
        boxstyle="round,pad=0.02,rounding_size=0.5",
        linewidth=1.2, edgecolor="black", facecolor="#E8F0FE",
    )
    ax.add_patch(box)
    _text(ax, x, y, text)


def process(ax, x, y, text):
    box = Rectangle(
        (x - W / 2, y - H / 2), W, H,
        linewidth=1.2, edgecolor="black", facecolor="white",
    )
    ax.add_patch(box)
    _text(ax, x, y, text)


def decision(ax, x, y, text):
    dw, dh = W * 1.15, H * 1.7
    diamond = Polygon(
        [(x, y + dh / 2), (x + dw / 2, y), (x, y - dh / 2), (x - dw / 2, y)],
        closed=True, linewidth=1.2, edgecolor="black", facecolor="#F0E8FE",
    )
    ax.add_patch(diamond)
    _text(ax, x, y, text)
    return dw, dh


def data(ax, x, y, text):
    skew = 0.4
    poly = Polygon(
        [
            (x - W / 2 + skew, y + H / 2),
            (x + W / 2,        y + H / 2),
            (x + W / 2 - skew, y - H / 2),
            (x - W / 2,        y - H / 2),
        ],
        closed=True, linewidth=1.2, edgecolor="black", facecolor="#E8FEEA",
    )
    ax.add_patch(poly)
    _text(ax, x, y, text)


def arrow(ax, x1, y1, x2, y2, label=None, label_offset=(0.18, 0)):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=14,
        linewidth=1.1, color="black",
        shrinkA=0, shrinkB=0,
    )
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + label_offset[0], my + label_offset[1], label,
                fontdict=FONT, ha="left", va="center",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"))


def main():
    fig, ax = plt.subplots(figsize=(8.5, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.5, 14)
    ax.set_aspect("equal")
    ax.axis("off")

    cx = 5.0
    side_x = 9.0  # колонка для обходной ветки "Нет"

    ys = {
        "start":    13.0,
        "load":     11.5,
        "detect":   10.0,
        "found":     8.3,
        "browsers": 6.3,
        "profiles": 4.8,
        "params":   3.3,
        "report":   1.7,
        "end":      0.3,
    }

    terminator(ax, cx, ys["start"],   "Начало")
    data      (ax, cx, ys["load"],    "Загрузить эталонные политики\nиз policies.json")
    process   (ax, cx, ys["detect"],  "Найти установленные браузеры\nи их профили")
    decision  (ax, cx, ys["found"],   "Хотя бы один\nбраузер найден?")
    process   (ax, cx, ys["browsers"],
               "Для каждого браузера:\nполучить версию, проверить процесс")
    process   (ax, cx, ys["profiles"],
               "Для каждого профиля: прочитать\nфайлы конфигурации и состояние")
    process   (ax, cx, ys["params"],
               "Для каждого параметра: вычислить\nитоговое значение и сравнить с эталоном")
    data      (ax, cx, ys["report"],  "Сформировать отчёт\nreport.txt")
    terminator(ax, cx, ys["end"],     "Конец")

    chain = ["start", "load", "detect", "found", "browsers",
             "profiles", "params", "report", "end"]
    dec_keys = {"found"}
    dh_full = H * 1.7  # высота ромба, см. decision()

    for prev, nxt in zip(chain[:-1], chain[1:]):
        y_top = ys[prev] - (dh_full / 2 if prev in dec_keys else H / 2)
        y_bot = ys[nxt]  + (dh_full / 2 if nxt  in dec_keys else H / 2)
        label = "Да" if prev == "found" else None
        arrow(ax, cx, y_top, cx, y_bot, label=label, label_offset=(0.2, 0))

    # Обходная ветка "Нет" из ромба "Браузеры найдены?" в "Сформировать отчёт"
    dec_right_x = cx + (W * 1.15) / 2
    arrow(ax, dec_right_x, ys["found"], side_x, ys["found"],
          label="Нет", label_offset=(-0.7, 0.2))
    arrow(ax, side_x, ys["found"], side_x, ys["report"])
    arrow(ax, side_x, ys["report"], cx + W / 2, ys["report"])

    ax.text(cx, 13.85,
            "Алгоритм автоматической проверки конфигурации браузеров",
            ha="center", va="bottom",
            fontdict={"family": "DejaVu Sans", "size": 12, "weight": "bold"})

    # Легенда — компактно, в одну строку под схемой
    legend_y = -1.0
    items = [
        ("Начало / конец", "#E8F0FE"),
        ("Действие",       "white"),
        ("Решение",        "#F0E8FE"),
        ("Данные",         "#E8FEEA"),
    ]
    swatch_w, swatch_h = 0.45, 0.32
    spacing = 2.45
    total_w = spacing * len(items)
    start_x = (10 - total_w) / 2

    for i, (label, color) in enumerate(items):
        x = start_x + i * spacing
        ax.add_patch(Rectangle(
            (x, legend_y - swatch_h / 2), swatch_w, swatch_h,
            edgecolor="black", facecolor=color, linewidth=1.0,
        ))
        ax.text(x + swatch_w + 0.12, legend_y, label,
                fontdict={"family": "DejaVu Sans", "size": 9}, va="center")

    plt.tight_layout()
    out_path = "flowchart.png"
    plt.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
