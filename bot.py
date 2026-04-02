cp /root/bot.py /root/bot_before_text_video_full_unlock.py

python3 - <<'PY'
from pathlib import Path
import re

p = Path('/root/bot.py')
text = p.read_text(encoding='utf-8')

original = text

# 1. Чиним callback выбора длительности для text-to-video
pat = r'if call\.data\.startswith\("video_text_dur_"\):.*?^\s*return\s*$'
m = re.search(pat, text, flags=re.S | re.M)
if not m:
    raise SystemExit("TEXT_DURATION_CALLBACK_NOT_FOUND")

replacement = '''if call.data.startswith("video_text_dur_"):
        parts = call.data.split("_")
        duration = int(parts[3])
        spent = int(parts[4])

        cursor.execute("SELECT tokens FROM users WHERE user_id=?", (user,))
        row = cursor.fetchone()

        if not row:
            bot.answer_callback_query(call.id, "❌ Профиль не найден.")
            return

        have = row[0]

        if have < spent:
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                insufficient_tokens_text(spent, have),
                reply_markup=buy_tokens_keyboard()
            )
            return

        active_video = get_user_active_video_tasks(user)

        if active_video >= 1:
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "⏳ У вас уже есть 1 активная видео-задача. Дождитесь завершения."
            )
            return

        prompt = pending_video_prompt.get(user, "")
        size = pending_video_size.get(user, "9:16")

        if duration not in [3, 5, 7, 10, 15]:
            duration = 5

        if size not in ["1:1", "9:16", "16:9"]:
            size = "9:16"

        enqueue_video_task(
            user_id=user,
            prompt=prompt,
            size=size,
            duration=duration,
            mode="text",
            photo_file_id="",
            ref_file_id=""
        )

        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"🎥 Видео поставлено в очередь\\n\\nРежим: text\\nРазмер: {size}\\nДлительность: {duration} сек"
        )
        return'''

text = text[:m.start()] + replacement + text[m.end():]

# 2. Чиним submit_kling_task только для режима text
pat2 = r'def submit_kling_task\(task\):.*?^\s*try:\s*\n\s*r = requests\.post\('
m2 = re.search(pat2, text, flags=re.S | re.M)
if not m2:
    raise SystemExit("SUBMIT_KLING_TASK_BLOCK_NOT_FOUND")

replacement2 = '''def submit_kling_task(task):
    mode = task.get("mode", "text")
    prompt = task.get("prompt", "")
    size = str(task.get("size", "9:16"))
    duration = int(task.get("duration", 5) or 5)
    photo_file_id = task.get("photo_file_id", "")
    ref_file_id = task.get("ref_file_id", "")
    task_id_local = task.get("task_id", "")

    if mode != "text":
        return {
            "ok": False,
            "reason": f"KLING_NOT_ENABLED_FOR_MODE_{mode}"
        }

    if duration not in [3, 5, 7, 10, 15]:
        duration = 5

    if size not in ["1:1", "9:16", "16:9"]:
        size = "9:16"

    payload = {
        "model_name": "kling-v2-6",
        "prompt": enhance_video_prompt_safe(prompt) if "enhance_video_prompt_safe" in globals() else prompt,
        "duration": str(duration),
        "mode": "pro",
        "sound": "off",
        "aspect_ratio": size,
        "external_task_id": str(task_id_local)
    }

    print("KLING TEXT INPUT:", {"duration": duration, "size": size, "mode": mode})

    try:
        r = requests.post('''

text = text[:m2.start()] + replacement2 + text[m2.end():]

if text == original:
    raise SystemExit("NO_CHANGES_MADE")

p.write_text(text, encoding='utf-8')
print("TEXT_VIDEO_FULL_UNLOCK_OK")
PY

sudo systemctl restart magicai-bot
sudo systemctl status magicai-bot
