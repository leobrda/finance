import os
from PIL import Image, ImageDraw, ImageFont


def create_neobrutalist_icon(size: int, output_path: str):
    # 1. Cria a base quadrada com fundo amarelo #FFE600
    bg_color = (255, 230, 0)  # #FFE600
    border_color = (0, 0, 0)  # #000000
    text_color = (0, 0, 0)  # Preto puro

    img = Image.new("RGB", (size, size), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 2. Desenha a borda sólida externa proporcional ao tamanho
    border_width = max(4, int(size * 0.04))  # ~8px no 192, ~20px no 512
    draw.rectangle(
        [(0, 0), (size - 1, size - 1)],
        outline=border_color,
        width=border_width
    )

    # 3. Tenta carregar uma fonte sem serifa pesada do sistema operacional
    font_size = int(size * 0.32)
    font = None

    # Fontes comuns grossas (Windows / Linux / Mac)
    font_candidates = [
        "arialbd.ttf",  # Arial Bold (Windows)
        "ariblk.ttf",  # Arial Black (Windows)
        "DejaVuSans-Bold.ttf",  # Linux
        "Helvetica-Bold.ttf"  # Mac/Unix
    ]

    for candidate in font_candidates:
        try:
            font = ImageFont.truetype(candidate, font_size)
            break
        except IOError:
            continue

    if font is None:
        font = ImageFont.load_default()

    # 4. Texto do ícone
    text = "FIN."

    # Calcula as dimensões do texto para centralizar precisamente
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) / 2
    # Ajuste vertical fino para compensar linha de base
    y = (size - text_height) / 2 - (bbox[1] / 2)

    # 5. Efeito sutil de sombra dura neobrutalista no texto (apenas no 512px)
    if size >= 512:
        offset = 6
        draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0, 60))

    draw.text((x, y), text, font=font, fill=text_color)

    # 6. Salva a imagem PNG otimizada
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, format="PNG")
    print(f"✓ Ícone gerado com sucesso: {output_path} ({size}x{size})")


if __name__ == "__main__":
    # Caminho onde o manifest.json e os templates procuram os ícones
    base_dir = os.path.join("static", "icons")

    create_neobrutalist_icon(192, os.path.join(base_dir, "icon-192x192.png"))
    create_neobrutalist_icon(512, os.path.join(base_dir, "icon-512x512.png"))