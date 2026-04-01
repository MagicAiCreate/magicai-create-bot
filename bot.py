python3 - <<'PY'
from pathlib import Path

p = Path('/root/bot.py')
text = p.read_text(encoding='utf-8')

# ===== 1. СУПЕР УСИЛЕНИЕ ПРОМТА (как у топ-ботов) =====
if "def enhance_video_prompt_v2(" not in text:
    insert = '''
def enhance_video_prompt_v2(prompt):
    base = prompt.strip()

    cinematic = (
        "cinematic film scene, ultra realistic, 8k, movie quality, "
        "professional lighting, dynamic lighting, volumetric light, shadows, "
        "depth of field, realistic textures, skin details, pores, natural motion, "
        "cinematic composition, film grain, lens blur, bokeh, realistic reflections"
    )

    environment = (
        "detailed environment, atmosphere, ambient light, realistic physics, "
        "depth layering, foreground middle background separation"
    )

    motion = (
        "smooth cinematic camera movement, steady tracking shot, "
        "subtle handheld motion, natural physics movement"
    )

    directing = (
        "realistic human behavior, natural gestures, believable movement, "
        "no stiff motion, no AI artifacts"
    )

    negative = (
        "low quality, blurry, cartoon, cheap, distorted, bad anatomy, "
        "oversaturated, unrealistic, low detail, artifacts, noise, jpeg artifacts"
    )

    return f"{base}, {cinematic}, {environment}, {motion}, {directing} --neg {negative}"
'''
    text = text.replace("def submit_kling_task", insert + "\n\ndef submit_kling_task", 1)

# ===== 2. УМНАЯ КАМЕРА (как у топ-ботов) =====
if "def choose_camera_v2(" not in text:
    insert = '''
def choose_camera_v2(prompt):
    p = prompt.lower()

    if any(w in p for w in ["бежит","погоня","бег"]):
        return {"type": "forward"}

    if any(w in p for w in ["толпа","улица","город","люди"]):
        return {"type": "forward_up"}

    if any(w in p for w in ["разговор","диалог","сидит"]):
        return {"type": "down_back"}

    if any(w in p for w in ["эпично","дрон","панорама"]):
        return {"type": "forward_up"}

    return {"type": "forward_up"}
'''
    text = text.replace("def submit_kling_task", insert + "\n\ndef submit_kling_task", 1)

# ===== 3. РАЗБИЕНИЕ НА СЦЕНЫ (самая важная фишка топ-ботов) =====
if "def build_multi_prompt(" not in text:
    insert = '''
def build_multi_prompt(prompt, duration):
    d = int(duration)

    if d <= 5:
        return [{"index":1,"prompt":enhance_video_prompt_v2(prompt),"duration":str(d)}]

    parts = []

    parts.append({
        "index":1,
        "prompt":enhance_video_prompt_v2(prompt + ", establishing shot, wide angle"),
        "duration":"3"
    })

    parts.append({
        "index":2,
        "prompt":enhance_video_prompt_v2(prompt + ", closer shot, more detail"),
        "duration":str(d-3)
    })

    return parts
'''
    text = text.replace("def submit_kling_task", insert + "\n\ndef submit_kling_task", 1)

# ===== 4. ПОЛНЫЙ ПАТЧ PAYLOAD =====
old = '''    payload = {
        "model_name": "kling-v2-6",
        "prompt": prompt,
        "duration": str(duration),
        "mode": "std",
        "sound": "off",
        "aspect_ratio": str(size),
        "external_task_id": str(task_id_local)
    }'''

new = '''    camera = choose_camera_v2(prompt)
    multi_prompt = build_multi_prompt(prompt, duration)

    payload = {
        "model_name": "kling-v2-6",
        "multi_prompt": multi_prompt,
        "multi_shot": True,
        "shot_type": "customize",
        "duration": str(duration),
        "mode": "pro",
        "sound": "off",
        "aspect_ratio": str(size),
        "camera_control": camera,
        "cfg_scale": 0.7,
        "external_task_id": str(task_id_local)
    }'''

if old not in text:
    print("PAYLOAD_NOT_FOUND")
    raise SystemExit

text = text.replace(old, new, 1)

p.write_text(text, encoding='utf-8')
print("ULTRA_PATCH_OK")
PY
