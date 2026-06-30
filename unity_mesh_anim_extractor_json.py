#!/usr/bin/env python3
"""
Unity 2D Mesh Animation Extractor (JSON version)
从 Unity JSON 资产中提取逐帧网格动画并渲染为 GIF/PNG

用法:
    python unity_mesh_anim_extractor_json.py <asset.json> <atlas.png> [options]
"""

import json
import argparse
import os
from PIL import Image, ImageDraw, ImageChops


def decode_uv_fixed16(val):
    """16.16 fixed-point UV 解码"""
    u = (val >> 16) / 65536.0
    v = (val & 0xFFFF) / 65536.0
    return (u, v)


def _solve_affine(dst, src):
    """求 PIL AFFINE 系数: 把输出(dst)坐标映射到源(src)坐标
    src_x = a*x + b*y + c, src_y = d*x + e*y + f"""
    (x0, y0), (x1, y1), (x2, y2) = dst
    det = x0 * (y1 - y2) - y0 * (x1 - x2) + (x1 * y2 - x2 * y1)
    if abs(det) < 1e-9:
        return None

    def coeffs(s0, s1, s2):
        a = (s0 * (y1 - y2) - y0 * (s1 - s2) + (s1 * y2 - s2 * y1)) / det
        b = (x0 * (s1 - s2) - s0 * (x1 - x2) + (x1 * s2 - x2 * s1)) / det
        c = (
            x0 * (y1 * s2 - y2 * s1)
            - y0 * (x1 * s2 - x2 * s1)
            + s0 * (x1 * y2 - x2 * y1)
        ) / det
        return a, b, c

    a, b, c = coeffs(src[0][0], src[1][0], src[2][0])
    d, e, f = coeffs(src[0][1], src[1][1], src[2][1])
    return (a, b, c, d, e, f)


def render_frame(
    frame_data,
    atlas_img,
    canvas_size=(800, 800),
    scale=120,
    offset=None,
    bg_color=(255, 255, 255, 255),
):
    """渲染单帧"""
    mesh = frame_data["MeshData"]
    vertices = [(v["x"], v["y"]) for v in mesh["Vertices"]]
    uvs_raw = mesh["UVs"]

    if offset is None:
        offset = (canvas_size[0] // 2, int(canvas_size[1] * 0.7))

    atlas_w, atlas_h = atlas_img.size
    canvas = Image.new("RGBA", canvas_size, bg_color)

    def to_screen(x, y):
        return (offset[0] + x * scale, offset[1] - y * scale)

    quad_count = len(vertices) // 4
    for qi in range(quad_count):
        vi = qi * 4
        if vi + 3 >= len(vertices):
            break

        quad_v = vertices[vi : vi + 4]
        screen_pts = [to_screen(x, y) for x, y in quad_v]

        ui = qi * 2
        if ui + 1 >= len(uvs_raw):
            continue

        uv1 = decode_uv_fixed16(uvs_raw[ui])
        uv2 = decode_uv_fixed16(uvs_raw[ui + 1])

        u_min, u_max = min(uv1[0], uv2[0]), max(uv1[0], uv2[0])
        v_min, v_max = min(uv1[1], uv2[1]), max(uv1[1], uv2[1])

        ax1 = max(0, int(u_min * atlas_w))
        ay1 = max(0, int((1 - v_max) * atlas_h))
        ax2 = min(atlas_w, int(u_max * atlas_w))
        ay2 = min(atlas_h, int((1 - v_min) * atlas_h))

        if ax2 <= ax1 or ay2 <= ay1:
            continue

        tex_slice = atlas_img.crop((ax1, ay1, ax2, ay2))
        sw, sh = tex_slice.size
        if sw < 2 or sh < 2:
            continue

        tex_corners = [(0, sh), (sw, sh), (sw, 0), (0, 0)]

        for tri in ((0, 1, 2), (0, 2, 3)):
            dst = [screen_pts[i] for i in tri]
            src = [tex_corners[i] for i in tri]

            xs = [p[0] for p in dst]
            ys = [p[1] for p in dst]
            min_x = max(0, int(min(xs)))
            min_y = max(0, int(min(ys)))
            max_x = min(canvas_size[0], int(max(xs)) + 1)
            max_y = min(canvas_size[1], int(max(ys)) + 1)
            box_w = max_x - min_x
            box_h = max_y - min_y
            if box_w < 1 or box_h < 1:
                continue

            coeffs = _solve_affine(dst, src)
            if coeffs is None:
                continue
            a, b, c, d, e, f = coeffs
            local = (a, b, c + a * min_x + b * min_y, d, e, f + d * min_x + e * min_y)

            warped = tex_slice.transform(
                (box_w, box_h), Image.Transform.AFFINE, local, resample=Image.BILINEAR
            )

            local_mask = Image.new("L", (box_w, box_h), 0)
            ImageDraw.Draw(local_mask).polygon(
                [(int(p[0]) - min_x, int(p[1]) - min_y) for p in dst], fill=255
            )
            warped.putalpha(ImageChops.multiply(warped.getchannel("A"), local_mask))

            region = canvas.crop((min_x, min_y, min_x + box_w, min_y + box_h))
            region = Image.alpha_composite(region, warped)
            canvas.paste(region, (min_x, min_y))

    return canvas


def extract_animation(
    asset_path,
    atlas_path,
    output_dir,
    sequence="standby",
    fps=24,
    canvas_size=None,
    scale=120,
    padding=16,
    export_gif=True,
    export_png=False,
    export_webp=False,
    webp_quality=100,
    transparent_bg=False,
):
    """主提取函数"""
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading asset: {asset_path}")
    with open(asset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loading atlas: {atlas_path}")
    atlas = Image.open(atlas_path).convert("RGBA")
    print(f"  Atlas size: {atlas.size}")

    # 查找序列
    sequences = data.get("Sequences", [])
    target = next((s for s in sequences if s["Name"] == sequence), None)
    if not target:
        raise ValueError(
            f'Sequence "{sequence}" not found. Available: {[s["Name"] for s in sequences]}'
        )

    frames = target["Frames"]
    fps = data.get("FrameRate", fps)
    print(f"Sequence '{sequence}': {len(frames)} frames @ {fps}fps")

    offset = None
    if canvas_size is None:
        verts = [v for f in frames for v in f["MeshData"]["Vertices"]]
        min_x = min(v["x"] for v in verts)
        max_x = max(v["x"] for v in verts)
        min_y = min(v["y"] for v in verts)
        max_y = max(v["y"] for v in verts)
        canvas_w = int(round((max_x - min_x) * scale)) + 2 * padding
        canvas_h = int(round((max_y - min_y) * scale)) + 2 * padding
        canvas_size = (canvas_w, canvas_h)
        offset = (padding - min_x * scale, padding + max_y * scale)
        print(f"  Auto-fit canvas: {canvas_size[0]}x{canvas_size[1]} (padding={padding})")

    bg = (0, 0, 0, 0) if transparent_bg else (255, 255, 255, 255)

    print("Rendering...")
    rendered = []
    for i, frame in enumerate(frames):
        img = render_frame(frame, atlas, canvas_size, scale, offset=offset, bg_color=bg)
        rendered.append(img)
        if export_png:
            img.save(os.path.join(output_dir, f"frame_{i:03d}.png"))
        if (i + 1) % max(1, len(frames) // 5) == 0:
            print(f"  {i + 1}/{len(frames)}")

    if export_gif:
        duration = int(1000 / fps)
        gif_path = os.path.join(output_dir, f"{sequence}.gif")
        rendered[0].save(
            gif_path,
            save_all=True,
            append_images=rendered[1:],
            duration=duration,
            loop=0,
            optimize=True,
        )
        print(f"GIF saved: {gif_path}")

    if export_webp:
        duration = int(1000 / fps)
        webp_path = os.path.join(output_dir, f"{sequence}.webp")
        save_kwargs = dict(
            save_all=True,
            append_images=rendered[1:],
            duration=duration,
            loop=0,
        )
        if webp_quality >= 100:
            save_kwargs["lossless"] = True
        else:
            save_kwargs["quality"] = webp_quality
        rendered[0].save(webp_path, format="WEBP", **save_kwargs)
        print(f"WebP saved: {webp_path}")

    print("Done!")
    return rendered


def main():
    parser = argparse.ArgumentParser(
        description="Extract Unity 2D mesh animation to GIF/PNG"
    )
    parser.add_argument("asset", help="Unity asset file (.json)")
    parser.add_argument("atlas", help="Atlas texture (.png)")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument(
        "-s", "--sequence", default="standby", help="Animation sequence name"
    )
    parser.add_argument("--fps", type=int, default=24, help="Frame rate (default: 24)")
    parser.add_argument(
        "--scale", type=float, default=120, help="Vertex scale multiplier"
    )
    parser.add_argument(
        "--width", type=int, default=None, help="Canvas width (omit for auto-fit)"
    )
    parser.add_argument(
        "--height", type=int, default=None, help="Canvas height (omit for auto-fit)"
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=16,
        help="Padding around content in auto-fit mode (default: 16)",
    )
    parser.add_argument(
        "--png", action="store_true", help="Export individual PNG frames"
    )
    parser.add_argument("--webp", action="store_true", help="Export animated WebP")
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=100,
        help="WebP quality 0-100 (100 = lossless, default: 100)",
    )
    parser.add_argument(
        "--transparent", action="store_true", help="Transparent background"
    )

    args = parser.parse_args()

    if args.width is not None and args.height is not None:
        canvas_size = (args.width, args.height)
    else:
        canvas_size = None

    extract_animation(
        asset_path=args.asset,
        atlas_path=args.atlas,
        output_dir=args.output,
        sequence=args.sequence,
        fps=args.fps,
        canvas_size=canvas_size,
        scale=args.scale,
        padding=args.padding,
        export_gif=True,
        export_png=args.png,
        export_webp=args.webp,
        webp_quality=args.webp_quality,
        transparent_bg=args.transparent,
    )


if __name__ == "__main__":
    main()
