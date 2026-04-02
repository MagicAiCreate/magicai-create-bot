cp /root/bot.py /root/bot_before_realism_final.py

python3 - <<'PY'
from pathlib import Path
import re

p = Path('/root/bot.py')
text = p.read_text(encoding='utf-8')

# 1. Универсальная очистка prompt для показа пользователю
cleanup_func = '''
def display_user_prompt_only(prompt):
    p = str(prompt or "")
    markers = [
        ", cinematic film scene",
        ", cinematic scene",
        ", cinematic, ultra realistic",
        ", ultra realistic",
        ", high detail",
        ", premium quality",
        ", professional cinematography",
        ", film lighting",
        ", volumetric light",
        ", soft shadows",
        ", depth of field",
        ", realistic textures",
        ", natural motion",
        ", smooth movement",
        ", sharp focus",
        ", detailed environment",
        ", realistic human behavior",
        ", cinematic camera",
        ", subtle camera movement",
        ", stable framing",
        ", natural composition",
        ", realistic proportions",
        ", realistic skin texture",
        ", believable physics",
        ", natural facial details",
        ", realistic clothing folds",
        ", realistic photo",
        ", ordinary natural appearance",
        ", natural face",
        ", everyday clothing",
        ", realistic hands",
        ", natural lighting",
        ", balanced detail",
        ", candid look",
        ", authentic scene",
        ", no glamour",
        ", no beauty idealization",
        ", true-to-life imperfections",
        " --neg ",
        "--neg "
    ]
    cut = len(p)
    for m in markers:
        i = p.find(m)
        if i != -1:
            cut = min(cut, i)
    return p[:cut].strip()


'''

if 'def display_user_prompt_only(prompt):' in text:
    text = re.sub(
        r"def display_user_prompt_only\(prompt\):.*?return p\[:cut\]\.strip\(\)\n\n",
        cleanup_func,
        text,
        flags=re.S
    )
else:
    pos = text.find('def build_video_result_caption')
    if pos == -1:
        pos = text.find('def build_result_caption')
    if pos == -1:
        pos = 0
    text = text[:pos] + cleanup_func + text[pos:]

# 2. Внутри caption-функций всегда чистим prompt перед показом
def ensure_cleanup_in_func(src, func_name):
    pat = rf"(def {func_name}\(prompt,[^\n]*\):\n)"
    m = re.search(pat, src)
    if not m:
        return src
    start = m.end()
    if src[start:start+40].find("prompt = display_user_prompt_only(prompt)") != -1:
        return src
    return src[:start] + "    prompt = display_user_prompt_only(prompt)\n" + src[start:]

for fn in ["build_video_result_caption", "build_result_caption", "build_image_result_caption"]:
    text = ensure_cleanup_in_func(text, fn)

# 3. Меняем скрытый промт на максимально реалистичный
old_positive = "cinematic film scene, ultra realistic, high detail, premium quality, professional cinematography, film lighting, volumetric light, soft shadows, depth of field, realistic textures, natural motion, smooth movement, sharp focus, detailed environment, realistic human behavior, cinematic camera, subtle camera movement, stable framing, natural composition, realistic proportions, realistic skin texture, believable physics, natural facial details, realistic clothing folds"
new_positive = "realistic photo, ordinary natural appearance, natural face, realistic skin texture, normal proportions, everyday clothing, realistic hands, natural lighting, balanced detail, candid look, authentic scene, no glamour, no beauty idealization, true-to-life imperfections"

old_negative = "low quality, blurry, cartoon, anime, cheap look, distorted anatomy, oversaturated colors, unrealistic motion, artifacts, noisy image, bad hands"
new_negative = "cartoon, anime, plastic skin, glamour look, beauty filter, doll face, distorted anatomy, bad hands, extra fingers, oversaturated colors, fake lighting, artifacts, noisy image"

text = text.replace(old_positive, new_positive)
text = text.replace(old_negative, new_negative)

# 4. Запасные замены для более коротких версий
text = text.replace(
    "cinematic, ultra realistic, high detail, film lighting, volumetric light, depth of field, realistic textures, natural motion, professional cinematography, sharp focus",
    "realistic photo, ordinary natural appearance, natural face, realistic skin texture, normal proportions, everyday clothing, realistic hands, natural lighting, balanced detail, candid look, authentic scene, no glamour, no beauty idealization, true-to-life imperfections"
)

text = text.replace(
    "low quality, blurry, cartoon, anime, cheap, distorted, bad anatomy, oversaturated, unrealistic, artifacts",
    "cartoon, anime, plastic skin, glamour look, beauty filter, doll face, distorted anatomy, bad hands, extra fingers, oversaturated colors, fake lighting, artifacts"
)

p.write_text(text, encoding='utf-8')
print("REALISM_AND_HIDE_FIXED")
PY

sudo systemctl restart magicai-bot
sudo systemctl status magicai-bot
